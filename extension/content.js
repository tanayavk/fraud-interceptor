console.log("Extension loaded");

document.getElementById("payBtn")?.addEventListener("click", async function (e) {
    e.preventDefault();

    const amount = document.getElementById("amount").value;
    const recipient = document.getElementById("recipient").value;

    try {
        const response = await fetch("http://127.0.0.1:8000/risk", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                user_id: "123",
                amount,
                recipient
            })
        });

        const data = await response.json();

        if (data.action === "BLOCK") {
            alert("Blocked: " + data.reasons.join(", "));
        } else {
            document.getElementById("paymentForm").submit();
        }

    } catch (err) {
        console.error(err);
        alert("Error connecting to backend");
    }
});