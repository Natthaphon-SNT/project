<?php
session_start();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="src.css">
    <title>Contacts</title>
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

        .main h2, h3 {
            
            color: #ddd;
            text-align: center;
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
            display:flex;
            justify-content: center;
            margin-bottom: 10px;
        }

        img {
            display: block;
            margin: 50px auto;
            width: 40%;
            height: auto;
        }

        .cover {
            
            background-color: #000;
            padding: 15px;
        }

        button {
            padding: 8px 15px;
            margin: 5px;
            border: 2px solid crimson;
            background-color: #000;
            color: #fff;
            cursor: pointer;
        }

        button a {
            color: #fff;
            text-decoration: none;
        }

        button:hover {
            background-color: crimson;
        }

        .button-container {
            display: flex;
            justify-content: center; /* Facebook ปุ่มอยู่ตรงกลาง */
            margin: 20px 0;
        }

        .top-buttons {
            display: flex;
            justify-content: flex-end;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 15px;
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
        <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 0px solid crimson; background-color: #000"><a href="login.php" style="text-decoration: none;"><i class="fa-regular fa-circle-user" style="font-size: 19px;"></i></a></button>
        <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 2px solid crimson; background-color: #000"><a href="contact.php" style="text-decoration: none;">Contact Us</a></button>
        <button style="display: flex; float: right;gap: 20px; margin: 0 5px; border: 2px solid crimson; background-color: #000"><a href="index.php" style="text-decoration: none;">Home</a></button>
        </div>

<h3 style="margin-top: 150px;">1). 116610905018-5  นายณัฐภณ ศรีนุต</h3>
<div class="button-container">
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://www.facebook.com/natthaphon.srinutta/" target="_blank" style="text-decoration: none;"><i class="fab fa-facebook" style="font-size:24px"></i></a></button>
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://line.me/ti/p/JhuaFkO0hu" target="_blank" style="text-decoration: none;"><i class="fa-brands fa-line" style="font-size:24px"></i></a></button>
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://www.instagram.com/ntp_snt_?igsh=ejlya2lqY3ozNDRq" target="_blank" style="text-decoration: none;"><i class="fa-brands fa-instagram" style="font-size:24px"></i></a></button>
</div>

<h3>2). 116610905009-4  นายนฤบดี มุกดากุล</h3>
<div class="button-container">
    
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://www.facebook.com/kao.narubodee" target="_blank" style="text-decoration: none;"><i class="fab fa-facebook" style="font-size:24px"></i></a></button>
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://line.me/ti/p/ywPQz65VJG" target="_blank" style="text-decoration: none;"><i class="fa-brands fa-line" style="font-size:24px"></i></a></button>
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://www.instagram.com/_kao.o_o_?igsh=MW9leGpnYXh2NGEweg==" target="_blank" style="text-decoration: none;"><i class="fa-brands fa-instagram" style="font-size:24px"></i></a></button>
</div>

<h3>3). 116610905109-2  นางสาวรัชต์ธร วงษ์แจ้ง</h3>
<div class="button-container">
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://www.facebook.com/share/19igzDV47E/?mibextid=wwXIfr" target="_blank" style="text-decoration: none;"><i class="fab fa-facebook" style="font-size:24px"></i></a></button>
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://line.me/ti/p/7MweTqPFSI" target="_blank" style="text-decoration: none;"><i class="fa-brands fa-line" style="font-size:24px"></i></a></button>
<button style="padding: 10px 20px; border: 2px solid crimson; background-color: #000; color: #fff;"><a href="https://www.instagram.com/sunx.sc?igsh=MXV3M2xrdTB4N3Zrcw%3D%3D&utm_source=qr" target="_blank" style="text-decoration: none;"><i class="fa-brands fa-instagram" style="font-size:24px"></i></a></button>
</div>
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