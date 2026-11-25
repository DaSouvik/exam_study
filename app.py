
import os
import io
import logging
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field
from dotenv import load_dotenv

from openai import OpenAI, OpenAIError

from docx import Document

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Preformatted,
    Spacer
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ExamForge AI",
    description="AI Question Paper Generator",
    version="1.0.0"
)


# ==========================================
# 2. STATIC FILES AND HTML TEMPLATES
# ==========================================

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )


# ==========================================
# 3. REQUEST DATA MODELS
# ==========================================

class PaperRequest(BaseModel):

    subject: str = Field(min_length=1, max_length=150)

    topic: str = Field(min_length=1, max_length=2000)

    marks: int = Field(ge=1, le=500)

    difficulty: str = Field(
        pattern="^(Easy|Medium|Hard|Mixed)$"
    )

    question_type: str = Field(
        pattern="^(Mixed|MCQ|Short Answer|Long Answer)$"
    )

    question_count: int = Field(ge=1, le=100)


class DownloadRequest(BaseModel):

    paper: str = Field(min_length=1, max_length=100000)


# ==========================================
# 4. OPENAI QUESTION PAPER GENERATOR
# ==========================================

def generate_question_paper(data: PaperRequest):

    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key is missing. Check your .env file."
        )

    client = OpenAI(api_key=API_KEY)

    prompt = f"""
You are an expert university examination paper setter.

Create a professional and academically accurate question paper.

EXAMINATION DETAILS:

Subject: {data.subject}

Topics: {data.topic}

Total Marks: {data.marks}

Difficulty Level: {data.difficulty}

Question Type: {data.question_type}

Number of Questions: {data.question_count}


INSTRUCTIONS:

1. Generate exactly {data.question_count} questions.
2. The total marks must equal exactly {data.marks}.
3. Distribute marks logically among all questions.
4. Cover the supplied topics.
5. Match the requested difficulty level.
6. Use clear and grammatically correct language.
7. Avoid duplicate and repetitive questions.
8. For MCQ, provide four options (A, B, C, D).
9. For Short Answer, create concise-answer questions.
10. For Long Answer, create descriptive questions.
11. For Mixed, include a suitable combination of question types.
12. Include question numbers and marks for every question.
13. Divide the paper into suitable sections if appropriate.
14. Include examination instructions.
15. Do not provide answers or solutions.
16. Do not invent a university name or official exam details.

OUTPUT FORMAT:

QUESTION PAPER

Subject: {data.subject}
Total Marks: {data.marks}
Difficulty: {data.difficulty}

General Instructions:
- Answer all questions unless stated otherwise.
- Marks are indicated against each question.

SECTION A
Questions...

SECTION B
Questions...

Ensure the marks distribution adds up correctly.
Return only the complete question paper as readable plain text.
"""

    try:

        response = client.responses.create(
            model=MODEL,
            instructions=(
                "You are a professional university examination "
                "paper generator. Follow the user's requirements "
                "accurately and return a well-structured paper."
            ),
            input=prompt,
            max_output_tokens=6000
        )

        paper = response.output_text.strip()

        if not paper:
            raise HTTPException(
                status_code=502,
                detail="AI returned an empty question paper."
            )

        return paper

    except OpenAIError as error:

        logger.exception("OpenAI API error")

        raise HTTPException(
            status_code=502,
            detail="AI generation failed. Check your API configuration and try again."
        ) from error


# ==========================================
# 5. GENERATE QUESTION PAPER ENDPOINT
# ==========================================

@app.post("/generate-paper")
def generate_paper(data: PaperRequest):

    paper = generate_question_paper(data)

    return {
        "success": True,
        "message": "Question paper generated successfully!",
        "paper": paper
    }


# ==========================================
# 6. DOWNLOAD TXT FILE
# ==========================================

@app.post("/download/txt")
def download_txt(data: DownloadRequest):

    file_content = data.paper.encode("utf-8")

    return StreamingResponse(
        io.BytesIO(file_content),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition":
                'attachment; filename="question_paper.txt"'
        }
    )


# ==========================================
# 7. DOWNLOAD PDF FILE
# ==========================================

def register_pdf_font():

    font_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    ]

    for font_path in font_candidates:

        if font_path.exists():

            pdfmetrics.registerFont(
                TTFont("ExamForgeFont", str(font_path))
            )

            return "ExamForgeFont"

    return "Helvetica"


@app.post("/download/pdf")
def download_pdf(data: DownloadRequest):

    buffer = io.BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    font_name = register_pdf_font()

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ExamTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    body_style = ParagraphStyle(
        "ExamBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=15
    )

    story = [
        Paragraph("EXAMFORGE AI", title_style),
        Spacer(1, 10),
        Preformatted(
            data.paper,
            body_style,
            maxLineLength=95
        )
    ]

    pdf.build(story)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                'attachment; filename="question_paper.pdf"'
        }
    )


# ==========================================
# 8. DOWNLOAD DOCX FILE
# ==========================================

@app.post("/download/docx")
def download_docx(data: DownloadRequest):

    document = Document()

    document.add_heading(
        "AI GENERATED QUESTION PAPER",
        level=1
    )

    for line in data.paper.splitlines():

        if line.strip():

            document.add_paragraph(line)

        else:

            document.add_paragraph("")

    buffer = io.BytesIO()

    document.save(buffer)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="question_paper.docx"'
        }
    )


# ==========================================
# 9. HEALTH CHECK
# ==========================================

@app.get("/health")
async def health_check():

    return {
        "status": "running",
        "application": "ExamForge AI",
        "ai_model_configured": bool(API_KEY)
    }
