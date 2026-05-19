<?php
session_start();
require 'db_conn.php';

ini_set('display_errors', 1);
error_reporting(E_ALL);

if (!isset($_SESSION['u_name'])) {
    header("Location: login.php");
    exit;
}

if (!isset($_GET['id'])) {
    die("<p style='color:red'>❌ ไม่พบรหัสสินค้าที่ต้องการแก้ไข</p>");
}

$product_id = $_GET['id'];


$stmt = $conn->prepare("SELECT * FROM products WHERE product_id = ? LIMIT 1");
$stmt->bind_param("s", $product_id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows === 0) {
    die("<p style='color:red'>❌ ไม่พบสินค้านี้ในระบบ</p>");
}

$product = $result->fetch_assoc();
$stmt->close();


if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $p_name = trim($_POST['p_name'] ?? '');
    $cid = trim($_POST['cid'] ?? '');
    $p_price = trim($_POST['p_price'] ?? '');
    $p_description = trim($_POST['p_description'] ?? '');
    $img_url = trim($_POST['img_url'] ?? '');
    $p_stock = (int)($_POST['p_stock'] ?? 0);

    if ($p_name === '' || $cid === '' || $p_price === '' || $p_stock === '') {
        $error = "⚠️ กรุณากรอกข้อมูลให้ครบถ้วน";
    } elseif (!is_numeric($p_price) || $p_price <= 0) {
        $error = "⚠️ ราคาต้องเป็นตัวเลขและมากกว่า 0";
    } else {
        $update = $conn->prepare("UPDATE products 
                                  SET p_name = ?, cid = ?, p_price = ?, p_description = ?, img_url = ?, p_stock = ?
                                  WHERE product_id = ?");
        $update->bind_param("ssdssis", $p_name, $cid, $p_price, $p_description, $img_url, $p_stock, $product_id);

        if ($update->execute()) {
            $success = "✅ แก้ไขข้อมูลสินค้าเรียบร้อยแล้ว";
            $product = [
                'p_name' => $p_name,
                'cid' => $cid,
                'p_description' => $p_description,
                'p_price' => $p_price,
                'p_stock' => $p_stock,
                'img_url' => $img_url,
            ];
        } else {
            $error = "❌ ไม่สามารถแก้ไขสินค้าได้: " . $update->error;
        }
        $update->close();
    }
}
?>

<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>แก้ไขสินค้า</title>
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
            background: #333;
            border-radius: 16px;
            box-shadow: 0 4px 20px crimson;
            text-align: center;
        }

        h1 {
            color: crimson;
        }

        input[type="text"],
        input[type="number"],
        textarea {
            color: #fff;
            width: 90%;
            padding: 8px;
            margin: 10px 0;
            font-size: 16px;
            border: 1px solid #555;
            border-radius: 6px;
            background-color: #333;
        }

        p label {
            color: #fff;
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
            background-color: #2d862d;
        }

        button {
            background-color: #1e90ff;
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

        img.preview {
            width: 200px;
            border-radius: 8px;
            margin-top: 10px;
        }
    </style>
</head>

<body>
    <div class="container">
        <h1>แก้ไขสินค้า: <?= htmlspecialchars($product_id) ?></h1>

        <?php 
        if (isset($error)) echo "<p class='message'>$error</p>"; 
        if (isset($success)) echo "<p class='success'>$success</p>"; 
        ?>

        <form method="post">
            <p><label>ชื่อสินค้า: </label>
            <input type="text" name="p_name" value="<?= htmlspecialchars($product['p_name']) ?>" ></p>

            <p><label>หมวดหมู่สินค้า (cid): </label>
            <input type="text" name="cid" value="<?= htmlspecialchars($product['cid']) ?>" ></p>

            <p><label>รายละเอียดสินค้า: </label>
            <textarea name="p_description"><?= htmlspecialchars($product['p_description']) ?></textarea></p>

            <p><label>ราคา: </label>
            <input type="number" step="0.01" name="p_price" value="<?= htmlspecialchars($product['p_price']) ?>" ></p>

            <p><label>จำนวนสินค้า: </label>
            <input type="number" name="p_stock" value="<?= htmlspecialchars($product['p_stock']) ?>"></p>
            

            <p><label>ลิงก์รูปภาพ: </label>
            <input type="text" name="img_url" value="<?= htmlspecialchars($product['img_url']) ?>" ></p>

            <?php if (!empty($product['img_url'])): ?>
                <img src="<?= htmlspecialchars($product['img_url']) ?>" alt="Product Image" class="preview">
            <?php endif; ?>

            <div class="form-action">
                <input type="submit" value="บันทึกการแก้ไข">
                <a href="index.php"><button type="button">กลับ</button></a>
                <!--<a href="admin_dashboard.php"><button type="button">กลับ</button></a>-->
            </div>
        </form>
    </div>
</body>
</html>
