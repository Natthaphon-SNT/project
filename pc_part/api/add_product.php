<?php
session_start();
require 'db_conn.php';

ini_set('display_errors', 1);
error_reporting(E_ALL);

if (!isset($_SESSION['u_name'])) {
    header("Location: login.php");
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $product_id = trim($_POST['product_id'] ?? '');
    $p_name = trim($_POST['p_name'] ?? '');
    $cid = trim($_POST['cid'] ?? '');
    $p_price = trim($_POST['p_price'] ?? '');
    $p_description = trim($_POST['p_description'] ?? '');
    $img_url = trim($_POST['img_url'] ?? '');

    if ($product_id === '' || $p_name === '' || $cid === '' || $p_price === '' || $img_url === '') {
        $error = "⚠️ กรุณากรอกข้อมูลให้ครบถ้วน";
    } elseif (!is_numeric($p_price) || $p_price <= 0) {
        $error = "⚠️ ราคาต้องเป็นตัวเลขและมากกว่า 0";
    } else {

        $check = $conn->prepare("SELECT product_id FROM products WHERE product_id = ?");
        $check->bind_param("s", $product_id);
        $check->execute();
        $check->store_result();

        if ($check->num_rows > 0) {
            $error = "❌ รหัสสินค้านี้มีอยู่แล้ว";
        } else {
            $check->close();

            $sql = "INSERT INTO products (product_id, p_name, cid, p_price, p_description, img_url)
                    VALUES (?, ?, ?, ?, ?, ?)";
            $stmt = $conn->prepare($sql);
            if ($stmt) {
                $stmt->bind_param("sssdss", $product_id, $p_name, $cid, $p_price, $p_description, $img_url);
                if ($stmt->execute()) {
                    $success = "✅ เพิ่มสินค้าเรียบร้อยแล้ว!";
                } else {
                    $error = "❌ ไม่สามารถเพิ่มสินค้าได้: " . $stmt->error;
                }
                $stmt->close();
            } else {
                $error = "❌ เกิดข้อผิดพลาด SQL: " . $conn->error;
            }
        }
    }
}
?>

<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>เพิ่มสินค้า</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #202020ff 0%, #000000ff 100%);
            margin: 0;
            padding: 0;
        }

        .container {
            
            max-width: 500px;
            margin: 60px auto;
            padding: 40px;
            background: #111;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(255, 50, 50, 0.3);
            text-align: center;
        }

        h1 {
            color: #ffffffff;
        }

        p {
            color: #fff;
        }

        input[type="text"],
        input[type="number"],
        textarea {
            width: 90%;
            padding: 8px;
            margin: 10px 0;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 6px;
        }

        textarea {
            height: 80px;
        }

        input[type="submit"], button {
            width: 120px;
            height: 40px;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            color: #fff;
        }

        input[type="submit"] {
            background-color: crimson;
            border: 2px solid #fff;
        }

        button {
            background-color: #202020ff;
            border: 2px solid crimson;
        }

        .form-action {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
        }

        p.message {
            color: red;
        }

        p.success {
            color: green;
        }
    </style>
</head>

<body>
    <div class="container">
        <h1>เพิ่มสินค้าใหม่</h1>

        <?php 
        if (isset($error)) echo "<p class='message'>$error</p>"; 
        if (isset($success)) echo "<p class='success'>$success</p>"; 
        ?>

        <form method="post">
            <p><label>รหัสสินค้า: </label>
            <input type="text" name="product_id" placeholder="EX. c01 cp01" required></p>

            <p><label>ชื่อสินค้า: </label>
            <input type="text" name="p_name" required></p>

            <p><label>หมวดหมู่สินค้า: </label>
            <input type="text" name="cid" placeholder="เช่น c01" required></p>

            <p><label>ราคา: </label>
            <input type="number" step="100" name="p_price" required></p>

            <p><label>รายละเอียดสินค้า: </label>
            <textarea name="p_description" placeholder="รายละเอียดเพิ่มเติม..."></textarea></p>

            <p><label>ลิงก์รูปภาพ: </label>
            <input type="text" name="img_url" placeholder="เช่น images/item.jpg" required></p>

            <div class="form-action">
                <input type="submit" value="เพิ่มสินค้า">
                <a href="index.php"><button type="button">กลับ</button></a>
                <!--<a href="admin_dashboard.php"><button type="button">กลับ</button></a>-->
            </div>
        </form>
    </div>
</body>
</html>
