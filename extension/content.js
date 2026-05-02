console.log("Aegis extension loaded");
// document.addEventListener("click", async function (e) {
//     if (e.target.id === "payBtn") {
//         e.preventDefault();

//         const amount = document.getElementById("amount").value;
//         const recipient = document.getElementById("recipient").value;

//         const response = await fetch("http://127.0.0.1:8000/risk", {
//             method: "POST",
//             headers: {"Content-Type": "application/json"},
//             body: JSON.stringify({amount, recipient})
//         });

//         const data = await response.json();

//         if (data.action === "BLOCK") {
//             alert("Blocked: " + data.reasons.join(", "));
//         } else {
//             document.getElementById("paymentForm").submit();
//         }
//     }
// });

document.addEventListener("click", function (e) {
    console.log("Clicked element:", e.target);
});