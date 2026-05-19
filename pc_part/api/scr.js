let currentSearch = " ";
let currentCategory = " ";

function searchProducts() {
    const query = document.getElementById("searchBox").value.toLowerCase();
    const products = document.querySelectorAll(".product-card");

    products.forEach(product => {
        const name = product.querySelector("h3").textContent.toLowerCase();
        if (name.includes(query)) {
            product.style.display = "block";
        } else {
            product.style.display = "none";
        }
    });
}

function handleKeyPress(event) {
    if (event.key === "Enter") {
        searchProducts();
    }
}

async function loadProducts() {
    const search = currentSearch || "";
    const category = currentCategory || "";

    const params = new URLSearchParams({ search, category });
    console.log("กำลังส่งพารามิเตอร์:", params.toString()); // debug

    try {
        const response = await fetch('s_products.php?' + params.toString());
        if (!response.ok) throw new Error("โหลดข้อมูลไม่สำเร็จ");
        
        const products = await response.json();
        console.log("ข้อมูลที่ได้จาก PHP:", products); // debug

        const container = document.getElementById('product-list');
        container.innerHTML = '';

        if (!products || products.length === 0) {
            container.innerHTML = '<p>ไม่พบสินค้า</p>';
            return;
        }

        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <img src="${p.img_url}">
                <h3>${p.p_name}</h3>
                <p>฿${p.p_price}</p>
                
                <form method="post" action="addcart.php">
                    <input type="hidden" name="product_id" value="${p.product_id}">
                    <input type="number" name="quantity" value="1" min="1">
                    <br><br>
                    <button type="submit">ใส่ตะกร้า</button>
                </form>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        console.error("เกิดข้อผิดพลาด:", err);
    }
}

const sidebar = document.getElementById('sidebar');
const content = document.getElementById('contentWrapper');
const categoriesBtn = document.getElementById('categoriesBtn');

categoriesBtn.addEventListener('click', () => {
  sidebar.classList.toggle('active');
  if (sidebar.classList.contains('active')) {
    content.style.marginLeft = sidebar.offsetWidth + 'px';
  } else {
    content.style.marginLeft = '0';
  }
});


/*
const filterBtn = document.getElementById('filterBtn');
const dropdown = document.getElementById('filterDropdown');

filterBtn.addEventListener('click', () => {
  dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
  
});
*/

document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const dropdown = document.getElementById(targetId);

        document.querySelectorAll('.filter-dropdown').forEach(d => {
            if (d !== dropdown) d.style.display = 'none';
        });

        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    });
});

const checkboxes = document.querySelectorAll('#filterDropdown input[type="checkbox"]');
checkboxes.forEach(checkbox => checkbox.addEventListener('change', filterProducts));

function filterProducts() {
  const keywords = Array.from(document.querySelectorAll('input[name="filter"]:checked'))
    .map(el => el.value.toLowerCase());

  document.querySelectorAll('.product-card').forEach(card => {
    const name = card.dataset.name;
    const desc = card.dataset.desc;

    if (keywords.length === 0) {
      card.style.display = 'block';
      return;
    }

    const match = keywords.some(keyword =>
      name.includes(keyword) || desc.includes(keyword)
    );

    card.style.display = match ? 'block' : 'none';
  });
}

document.addEventListener('click', (e) => {
  if (!filterBtn.contains(e.target) && !filterDropdown.contains(e.target)) {
    filterDropdown.style.display = 'none';
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const checkboxes = document.querySelectorAll('input[name="filter"]');
  const productList = document.getElementById("product-list");
  const searchBox = document.getElementById("searchBox");


  checkboxes.forEach(cb => {
    cb.addEventListener("change", applyFilters);
  });

  
  searchBox.addEventListener("input", applyFilters);

  function applyFilters() {
    const keyword = searchBox.value.toLowerCase();
    const selectedFilters = Array.from(checkboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value.toLowerCase());

    const cards = document.querySelectorAll(".product-card");

    cards.forEach(card => {
      const name = card.querySelector("h3").innerText.toLowerCase();
      const desc = card.innerText.toLowerCase();

      const matchesKeyword =
        keyword === "" || name.includes(keyword) || desc.includes(keyword);

      const matchesFilter =
        selectedFilters.length === 0 ||
        selectedFilters.some(f => name.includes(f) || desc.includes(f));

      
      if (matchesKeyword && matchesFilter) {
        card.style.display = "block";
      } else {
        card.style.display = "none";
      }
    });
  }
});



