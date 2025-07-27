const firebaseURL = "https://bot-9dce9-default-rtdb.firebaseio.com/orders.json";

function loadData() {
  fetch(firebaseURL)
    .then(res => res.json())
    .then(data => {
      let total = 0;
      const table = document.getElementById("orderTable");
      table.innerHTML = "";

      if (!data) {
        table.innerHTML = "<tr><td colspan='5' class='text-center'>No orders found.</td></tr>";
        return;
      }

      Object.keys(data).reverse().forEach(key => {
        const order = data[key];
        total += order.price || 0;

        const row = `
          <tr>
            <td>${order.user_id}</td>
            <td><a href="${order.link}" target="_blank">${order.link}</a></td>
            <td>${order.views}</td>
            <td>$${(order.price || 0).toFixed(2)}</td>
            <td>${order.time || "-"}</td>
          </tr>`;
        table.innerHTML += row;
      });

      document.getElementById("totalIncome").innerText = "$" + total.toFixed(2);
    })
    .catch(err => {
      console.error("Error loading orders:", err);
      document.getElementById("orderTable").innerHTML = "<tr><td colspan='5'>❌ Error loading data</td></tr>";
    });
}

// Load on first visit
loadData();