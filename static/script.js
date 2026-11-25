
const paperForm = document.getElementById("paperForm");
const generateBtn = document.getElementById("generateBtn");
const result = document.getElementById("result");

let generatedPaper = "";

// GENERATE QUESTION PAPER
paperForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const data = {
        subject: document.getElementById("subject").value.trim(),
        topic: document.getElementById("topic").value.trim(),
        marks: Number(document.getElementById("marks").value),
        difficulty: document.getElementById("difficulty").value,
        question_type: document.getElementById("questionType").value,
        question_count: Number(
            document.getElementById("questionCount").value
        )
    };

    if (!data.subject || !data.topic) {
        alert("Please fill in all required fields.");
        return;
    }

    generateBtn.disabled = true;
    generateBtn.innerHTML = "Generating your paper...";

    result.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">
                <i data-lucide="loader-circle"></i>
            </div>
            <h3>AI is creating your question paper...</h3>
            <p>Please wait while your paper is being generated.</p>
        </div>
    `;

    if (window.lucide) lucide.createIcons();

    try {
        const response = await fetch("/generate-paper", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error("Failed to generate question paper.");
        }

        const responseData = await response.json();

        generatedPaper = responseData.paper;

        if (!generatedPaper) {
            throw new Error("No question paper was returned.");
        }

        result.innerHTML = `
            <div class="paper-content">
                <h3>✨ Generated Question Paper</h3>
                <pre></pre>
            </div>
        `;

        result.querySelector("pre").textContent = generatedPaper;

        document.querySelector(".preview-section").scrollIntoView({
            behavior: "smooth"
        });

    } catch (error) {
        result.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <i data-lucide="alert-circle"></i>
                </div>
                <h3>Generation Failed</h3>
                <p></p>
            </div>
        `;

        result.querySelector(".empty-state p").textContent =
            error.message + " Please check your FastAPI backend.";

        if (window.lucide) lucide.createIcons();

    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = `
            <i data-lucide="sparkles"></i>
            Generate Question Paper
            <i data-lucide="arrow-right"></i>
        `;

        if (window.lucide) lucide.createIcons();
    }
});


// DOWNLOAD FILES
document.querySelectorAll(".export-btn").forEach(button => {

    button.addEventListener("click", async function () {

        const format = this.dataset.format;

        if (!generatedPaper) {
            alert("Please generate a question paper first.");
            return;
        }

        try {
            const response = await fetch(
                `/download/${format}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        paper: generatedPaper
                    })
                }
            );

            if (!response.ok) {
                throw new Error("Download failed.");
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            const link = document.createElement("a");
            link.href = url;
            link.download = `question_paper.${format}`;

            document.body.appendChild(link);
            link.click();
            link.remove();

            URL.revokeObjectURL(url);

        } catch (error) {
            alert(error.message + " Please check your backend.");
        }

    });

});
