<?php
session_start();
include "db_conn.php";

if (!isset($_GET['id'])) {
    die("<p>❌ ไม่พบสินค้าที่เลือก</p>");
}

$id = $_GET['id'];

$stmt = $conn->prepare("SELECT * FROM products WHERE product_id = ?");
$stmt->bind_param("s", $id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows == 0) {
    die("<p>❌ ไม่พบสินค้านี้ในฐานข้อมูล</p>");
}

$product = $result->fetch_assoc();
?>

<!DOCTYPE html>
<html lang="th">

<head>
    <meta charset="UTF-8">
    <title><?php echo htmlspecialchars($product['p_name']); ?></title>
    <link rel="stylesheet" href="src.css">
    <script src="https://kit.fontawesome.com/ecdaf24e6f.js" crossorigin="anonymous"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #202020;
            color: #fff;
            margin: 0;
            padding: 0;
        }

        .containere {
            max-width: 1000px;
            margin: 50px auto;
            padding: 0 20px;
        }

        .product-cardd {
            display: flex;
            flex-wrap: wrap;
            background: #111;
            border-radius: 10px;
            padding: 30px;
            gap: 20px;
            border: 1px solid #333;
            box-shadow: 0 0 15px rgba(255, 50, 50, 0.3);
        }

        .product-cardd img {
            width: 300px;
            height: 300px;
            position: relative;
            border-radius: 10px;
            flex-shrink: 0;
        }

        .product-info {
            flex: 1;
        }

        .product-info h1 {
            font-size: 32px;
            margin-bottom: 15px;
            color: crimson;
        }

        .product-info p {
            font-size: 16px;
            line-height: 1.5;
        }

        .product-info label {
            margin-right: 10px;
        }

        button {
            background-color: #202020ff;
            border: 2px solid crimson;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }

        button:hover {
            background-color: darkred;
        }

        button a :hover {
            background-color: darkred;
        }

        .add-cart,
        .buy-now {
            display: inline-block;
            margin-right: 15px;
        }

        .product-cardd .stock {
            color: green;
            font-weight: bold;
            margin: 5px 0;
        }

        input[type="number"] {
            width: auto;
            height: 30px;
            padding: 5px 5px;
            text-align: center;
            border: 1px solid #666;
            border-radius: 5px;
        }

        @media(max-width:800px) {
            .product-card {
                flex-direction: column;
                align-items: center;
                text-align: center;
            }

            .product-info {
                width: 100%;
            }
        }
    </style>
</head>

<body>

    <div class="containere">
        <div class="product-cardd">
            <img src="<?php echo htmlspecialchars($product['img_url']); ?>" alt="<?php echo htmlspecialchars($product['p_name']); ?>">

            <div class="product-info">
                <h1><?php echo htmlspecialchars($product['p_name']); ?></h1>

                <p>รหัสสินค้า : <?php echo ($product['product_id']) ?></p>
                <hr>
                <h1><strong>ราคา : </strong> ฿<?php echo number_format($product['p_price']); ?></h1>
                <p><strong>รายละเอียด : </strong><br><?php echo nl2br(htmlspecialchars($product['p_description'])); ?></p>

                <p class="stock"><strong>คงเหลือ : </strong> <?php echo $product['p_stock']; ?> ชิ้น</p>

                <form method="post" action="add_product_cart.php" class="add-cart">
                    <input type="hidden" name="product_id" value="<?php echo htmlspecialchars($product['product_id']); ?>">
                    <input type="hidden" name="p_name" value="<?php echo htmlspecialchars($product['p_name']); ?>">
                    <input type="hidden" name="p_price" value="<?php echo $product['p_price']; ?>">
                    <input type="hidden" name="img_url" value="<?php echo htmlspecialchars($product['img_url']); ?>">
                    <br>
                    <label>จำนวน : </label>
                    <input type="number" name="quantity" value="1" min="1" style="width:60px; padding:5px; text-align:center;margin-right: 20px">
                    <button type="submit" style="background-color:#202020ff;border: 2px solid crimson; color: #fff;">เพิ่มลงตะกร้า</button>
                </form>
                <br>
                <br>
                <a href="index.php" style="background-color:#202020ff; color: #fff; margin-right: 30px;"><button type="submit" style="background-color:#202020ff;border: 2px solid crimson; color: #fff;">Back</button></a>
                <form method="post" action="buy_now.php" class="buy-now">
                    <input type="hidden" name="product_id" value="<?php echo htmlspecialchars($product['product_id']); ?>">
                    <input type="hidden" name="p_name" value="<?php echo htmlspecialchars($product['p_name']); ?>">
                    <input type="hidden" name="p_price" value="<?php echo $product['p_price']; ?>">
                    <input type="hidden" name="img_url" value="<?php echo htmlspecialchars($product['img_url']); ?>">
                    <input type="hidden" name="quantity" value="1">
                    <button type="submit" style="background-color:#202020ff;border: 2px solid crimson; color: #fff;">สั่งซื้อทันที</button>
                </form>

            </div>
        </div>
    </div>

</body>

</html>