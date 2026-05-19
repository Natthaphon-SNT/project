<?php
include "db_conn.php";
include "header.php";

if (!isset($_SESSION['uid'])) {
    echo "<script>alert('กรุณาเข้าสู่ระบบก่อน'); window.location.href='login.php';</script>";
    exit;
}

$role = $_SESSION['u_role'] ?? 'customer';
$sql = "SELECT * FROM products where cid = 'c02' ORDER BY cid ASC";
$promo_sql = "SELECT * FROM promotions WHERE status = 'active' ORDER BY promo_id DESC";
$promo_result = $conn->query($promo_sql);


$result = $conn->query($sql);


?>

<!DOCTYPE html>
<html lang="th">

<head>
    <meta charset="UTF-8">
    <title>ร้านขายอุปกรณ์คอม</title>
    <link rel="stylesheet" href="src.css">
    <script src="https://kit.fontawesome.com/ecdaf24e6f.js" crossorigin="anonymous"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background: #202020ff;
        }

        .main {
            flex: 1;
            /* ดัน footer ลงล่าง */
            padding: 20px;

        }

        footer {
            background: #000;
            color: #fff;
            text-align: center;
            padding: 15px 0;
            border-top: 1px solid #555;
        }

        .sidebar {
            width: 200px;
            background: rgb(0, 0, 0);
            padding: 20px;
            height: 100vh;
            color: #fff;
            display: block;
        }



        .main h2 {
            color: #fff;
        }

        input[type="number"] {
            width: auto;
            height: 30px;
            padding: 5px 5px;
            text-align: center;
            border: 1px solid #666;
            border-radius: 5px;
        }

        .search {
            top: 0;
            display: flex;

            right: -20px;
        }

        p img {
            align-items: center;
            content: center;
            width: 900px;
            height: 500px;
            margin: 50px 400px;
            border-radius: 10px;

        }
    </style>
</head>

<body>


    <div class="sidebar" id="sidebar">
        <br>
        <ul>

            <li><button><a href="index.php"><i class="fa-solid fa-gears fa-bounce"></i> All Products</a></button></li>
            <li><button><a href="cpu.php"><i class="fa-solid fa-microchip fa-bounce"></i> CPU</a></button></li>
            <li><button><a href="mb.php"><i class="fa-solid fa-microchip fa-bounce"></i> Mainboard</a></li></button>
            <li><button><a href="gpu.php"><i class="fa-solid fa-sim-card fa-bounce"></i> Graphic card</a></li></button>
            <li><button><a href="ram.php"><i class="fa-solid fa-memory fa-bounce"></i> RAM</a></li></button>
            <li><button><a href="m2.php"><i class="fa-solid fa-hard-drive fa-bounce"></i> M.2</a></li></button>
            <li><button><a href="psu.php"><i class="fa-solid fa-car-battery fa-bounce"></i> Power supply</a></li></button>
            <li><button><a href="case.php"><i class="fa-solid fa-box fa-bounce"></i> Case</a></li></button>
            <li><button><a href="lqc.php"><i class="fa-solid fa-fan fa-bounce"></i> Liquid Cooler</a></li></button>
            <li><button><a href="arc.php"><i class="fa-solid fa-fan fa-bounce"></i> Air Cooler</a></li></button>
        </ul>
    </div>

    <div class="main">
        <div class="cover">
            <div class="search">
                <input type="text" id="searchBox" placeholder="ค้นหาสินค้า..." onkeypress="handleKeyPress(event)">
                <?php if ($role === 'admin'): ?>
                    <button style="border: 2px solid crimson; background-color: #000; margin-right: 20px;">
                        <a href="admin_orders.php" style="color: #fff; text-decoration: none;">Orders Sys</a>
                    </button>
                    <button style="border: 2px solid crimson; background-color: #000; margin-right: 20px;">
                        <a href="add_product.php" style="color: #fff; text-decoration: none;">+ เพิ่มสินค้า</a>
                    </button>
                    <button style="border: 2px solid crimson; background-color: #000;">
                        <a href="add_promo.php" style="color: #fff; text-decoration: none;">+ เพิ่มโปรโมชั่น</a>
                    </button>

                <?php endif; ?>
            </div>

            <button id="categoriesBtn" style="border: 2px solid crimson; background-color: #000;">Categories</button>
            <button style="display: flex; float: right;gap: 10px; margin: 0 5px; border: 0px solid crimson; background-color: #000;color: #fff"><a href="viewcart.php" style="text-decoration: none; color: #fff"><i class="fa-solid fa-cart-shopping" style="font-size: 18px;"></i></a></button>
            <button style="display: flex; float: right;gap: 10px; margin: 0 5px; border: 0px solid crimson; background-color: #000"><a href="login.php" style="text-decoration: none;color: #fff"><i class="fa-regular fa-circle-user" style="font-size: 19px;"></i></a></button>
            <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 2px solid crimson; background-color: #000"><a href="contact.php" style="text-decoration: none;color: #fff">Contact Us</a></button>
            <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 2px solid crimson; background-color: #000"><a href="index.php" style="text-decoration: none;color: #fff">Home</a></button>
            <div class="under">
            <div class="filter-group">
            <button data-target="brandFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">Brand <i class="fa-solid fa-caret-down"></i></button>
            <div id="brandFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="ASROCK"> ASROCK</label><br>
                    <label><input type="checkbox" name="filter" value="ASUS"> ASUS</label><br>
                    <label><input type="checkbox" name="filter" value="COLORFUL"> COLORFUL</label><br>
                    <label><input type="checkbox" name="filter" value="GIGABYTE"> GIGABYTE</label><br>
                    <label><input type="checkbox" name="filter" value="MSI"> MSI</label>
                    
                </div>
            </div>
            </div>

            <div class="filter-group">
            <button data-target="supFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">CPU Support <i class="fa-solid fa-caret-down"></i></button>
            <div id="supFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="12th Gen"> 12th Gen</label><br>
                    <label><input type="checkbox" name="filter" value="14th Gen"> 14th Gen</label><br>
                    <label><input type="checkbox" name="filter" value="CORE ULTRA"> CORE ULTRA</label><br>
                    <label><input type="checkbox" name="filter" value="5000 Series"> 5000 Series</label><br>
                    <label><input type="checkbox" name="filter" value="7000 Series"> 7000 Series</label><br>
                    <label><input type="checkbox" name="filter" value="8000 Series"> 8000 Series</label><br>
                    <label><input type="checkbox" name="filter" value="9000 Series"> 9000 Series</label><br>
                    <label><input type="checkbox" name="filter" value="PRO 4000 Series"> PRO 4000 Series</label>
                    
                </div>  
            </div>
            </div>

            <div class="filter-group">
            <button data-target="proFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">Processor <i class="fa-solid fa-caret-down"></i></button>
            <div id="proFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="Ryzen 5"> Ryzen 5</label><br>
                    <label><input type="checkbox" name="filter" value="Ryzen 7"> Ryzen 7</label><br>
                    <label><input type="checkbox" name="filter" value="Ryzen 9"> Ryzen 9</label><br>
                    <label><input type="checkbox" name="filter" value="Core i5"> Core i5</label><br>
                    <label><input type="checkbox" name="filter" value="Core i7"> Core i7</label><br>
                    <label><input type="checkbox" name="filter" value="Core i9"> Core i9</label>
                    
                </div>  
            </div>
            </div>

            <div class="filter-group">
            <button data-target="socketFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">Socket Type <i class="fa-solid fa-caret-down"></i></button>
            <div id="socketFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="AM4"> AM4</label><br>
                    <label><input type="checkbox" name="filter" value="AM5"> AM5</label><br>
                    <label><input type="checkbox" name="filter" value="LGA 1700"> LGA 1700</label><br>
                    <label><input type="checkbox" name="filter" value="LGA 1851"> LGA 1851</label> 
                    
                </div>  
            </div>
            </div>

            <div class="filter-group">
            <button data-target="mbFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">Mainboard Support <i class="fa-solid fa-caret-down"></i></button>
            <div id="mbFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="E-ATX"> E-ATX</label><br>
                    <label><input type="checkbox" name="filter" value="ATX"> ATX</label><br>
                    <label><input type="checkbox" name="filter" value="Mini-ATX"> Mini-ATX</label><br>
                    <label><input type="checkbox" name="filter" value="Micro-ATX"> Micro-ATX</label><br>  
                    <label><input type="checkbox" name="filter" value="LGA 1851"> M-ATX</label>
                    
                </div>  
            </div>
            </div>

            <div class="filter-group">
            <button data-target="mmFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">Memory Slots <i class="fa-solid fa-caret-down"></i></button>
            <div id="mmFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="2xDIMM"> 2 x DIMM</label><br>
                    <label><input type="checkbox" name="filter" value="4xDIMM"> 4 x DIMM</label>
                    
                </div>  
            </div>
            </div>

            <div class="filter-group">
            <button data-target="mtFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">Memory Type <i class="fa-solid fa-caret-down"></i></button>
            <div id="mtFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="DDR5"> DDR5</label><br>
                    <label><input type="checkbox" name="filter" value="DDR4"> DDR4</label>
                    
                </div>  
            </div>
            </div>

            <div class="filter-group">
            <button data-target="maxmemFilter" class="filter-btn" style="border: 2px solid white; background-color: crimson; color: #fff; text-decoration: none;">Max Memory <i class="fa-solid fa-caret-down"></i></button>
            <div id="maxmemFilter" class="filter-dropdown">
                <div class="filter-section">
                    <label><input type="checkbox" name="filter" value="64GB"> 64GB</label><br>
                    <label><input type="checkbox" name="filter" value="96GB"> 96GB</label><br>
                    <label><input type="checkbox" name="filter" value="128GB"> 128GB</label><br>
                    <label><input type="checkbox" name="filter" value="192GB"> 192GB</label><br>
                    <label><input type="checkbox" name="filter" value="256GB"> 256GB</label><br>
                    <label><input type="checkbox" name="filter" value="4096GB"> 4096GB</label><br>
                    <label><input type="checkbox" name="filter" value="128GB (2x 64GB)"> 128GB (2x 64GB)</label>
                    
                </div>  
            </div>
            </div>
            </div>
            </div>
            
        
        <hr style="margin: 100px 0; border: 1px solid #444;">

        <h2>Mainboard Products</h2>
        <div id="product-list" class="product-grid">
            <?php while ($row = $result->fetch_assoc()): ?>
                <div class="product-card">
                    <span class="hidden" style="display: none;">
                        data-name="<?php echo htmlspecialchars($row['p_name'], ENT_QUOTES); ?>"
                        data-description="<?php echo htmlspecialchars($row['p_description'], ENT_QUOTES); ?>">
                    </span>
                    <a href="product_dtail.php?id=<?php echo urlencode($row['product_id']); ?>">
                        <img src="<?php echo htmlspecialchars($row['img_url']); ?>" alt="<?php echo htmlspecialchars($row['p_name']); ?>">
                        <h3><?php echo htmlspecialchars($row['p_name']); ?></h3>
                    </a>
                    <p class="description" style="color: #ccc;"><?php echo htmlspecialchars($row['p_description']); ?></p>
                    <p class="price">฿<?php echo number_format($row['p_price']); ?></p>
                    <!--<p class="stock">คงเหลือ: <?php echo $row['p_stock']; ?> ชิ้น</p>-->
                    <?php if ($role === 'customer'): ?>
                        <form method="post" action="add_product_cart.php">
                            <input type="hidden" name="product_id" value="<?php echo $row['product_id']; ?>">
                            <input type="hidden" name="p_name" value="<?php echo htmlspecialchars($row['p_name'], ENT_QUOTES); ?>">
                            <input type="hidden" name="p_descrption" value="<?php echo htmlspecialchars($row['p_description']); ?>">
                            <input type="hidden" name="p_price" value="<?php echo $row['p_price']; ?>">
                            <input type="hidden" name="img_url" value="<?php echo htmlspecialchars($row['img_url'], ENT_QUOTES); ?>">
                            <input type="number" name="quantity" value="1" min="1">
                            <br>
                            <br>
                            <button onclick="addToCart('<?php echo $row['p_name']; ?>')">ใส่ตะกร้า</button>

                        </form>
                    <?php elseif ($role === 'admin'): ?>
                        <div class="admin-btns">
                            <button onclick="window.location.href='edit_product.php?id=<?php echo $row['product_id']; ?>'">แก้ไข</button>
                            <button onclick="if(confirm('ยืนยันการลบสินค้า?')) window.location.href='delete_product.php?id=<?php echo $row['product_id']; ?>'">ลบ</button>
                        </div>
                    <?php endif; ?>
                </div>
            <?php endwhile; ?>
        </div>
    </div>

    <script src="scr.js"></script>
    <script src="pic.js"></script>

    <footer>
        <h3>Facebook</h3>
        <h3>Line</h3>
        <h3>IG</h3>

    </footer>
</body>

</html>