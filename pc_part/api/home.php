<?php
include "db_conn.php";
include "header.php";
?>

<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>Home</title>
<link rel="stylesheet" href="src.css">
<script src="https://kit.fontawesome.com/ecdaf24e6f.js" crossorigin="anonymous"></script>
<style>
    body {
  font-family: Arial, sans-serif;
  margin: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #373737;
}

.main {
  flex: 1; /* ดัน footer ลงล่าง */
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
            display:flex;
            
            right: -20px;
        }
    img {
        display: block;
        width: 40%;
        height: auto;
        margin: 50px auto;
    }

    .cover {
            background-color: #000;
        }

    h1, h2, h3 {
        text-align: center;
        align-items: center;
        color: #ffffffff;
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
        
        </div>
        <button id="categoriesBtn" style="border: 2px solid crimson; background-color: #000;">Categories</button>
        <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 0px solid crimson; background-color: #000"><a href="viewcart.php" style="text-decoration: none;"><i class="fa-solid fa-cart-shopping" style="font-size: 18px;"></i></a></button>
        <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: จpx solid crimson; background-color: #000"><a href="edit_profile.php" style="text-decoration: none;"><i class="fa-regular fa-circle-user" style="font-size: 19px;"></i></a></button>
        <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 2px solid crimson; background-color: #000"><a href="contact.php" style="text-decoration: none;">Contact Us</a></button>
        <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 2px solid crimson; background-color: #000"><a href="home.php" style="text-decoration: none;">Home</a></button>
        </div>
<h1 style="margin-top: 100px;">Welcome to our Mini Project</h1>
<h2>Members :</h2>
<h3>116610905018-5  นายณัฐภณ ศรีนุต</h3>
<h3>116610905009-4  นายนฤบดี มุกดากุล</h3>
<h3>116610905109-2  นางสาวรัชต์ธร วงษ์แจ้ง</h3>
<hr>
<img src="self.jpg" alt="">

<script src="scr.js"></script>
<footer>
        <span>
            <h3>Facebook</h3>
        <h3>Line</h3>
        <h3>IG</h3>
        </span>

    </footer>
</body>
</html>
