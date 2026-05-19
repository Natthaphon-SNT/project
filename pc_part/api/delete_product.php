<?php
session_start();
require 'db_conn.php';

ini_set('display_errors', 1);
error_reporting(E_ALL);

if (!isset($_SESSION['u_role']) || $_SESSION['u_role'] !== 'admin') {
    die("<p style='color:red;'>⛔ คุณไม่มีสิทธิ์ในการลบสินค้า</p>");
}

if (!isset($_GET['id'])) {
    die("<p style='color:red;'>❌ ไม่พบรหัสสินค้าที่ต้องการลบ</p>");
}

$product_id = $_GET['id'];

$stmt = $conn->prepare("SELECT * FROM products WHERE product_id = ? LIMIT 1");
$stmt->bind_param("s", $product_id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows === 0) {
    die("<p style='color:red;'>❌ ไม่พบสินค้านี้ในระบบ</p>");
}

$product = $result->fetch_assoc();
$stmt->close();

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['confirm_delete'])) {
    $delete = $conn->prepare("DELETE FROM products WHERE product_id = ?");
    $delete->bind_param("s", $product_id);

    if ($delete->execute()) {
        echo "<script>alert('✅ ลบสินค้าเรียบร้อยแล้ว'); window.location.href='index.php';</script>";
        //echo "<script>alert('✅ ลบสินค้าเรียบร้อยแล้ว'); window.location.href='admin_dashboard.php';</script>";
        exit;
    } else {
        $error = "❌ ไม่สามารถลบสินค้าได้: " . $delete->error;
    }
    $delete->close();
}
?>

<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ลบสินค้า</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%);
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 500px;
            margin: 60px auto;
            padding: 40px;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            text-align: center;
        }

        h1 {
            color: #d32f2f;
        }

        img {
            width: 200px;
            border-radius: 10px;
            margin-top: 10px;
        }

        p {
            font-size: 18px;
        }

        .btn {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            margin: 10px;
        }

        .confirm {
            background-color: #d32f2f;
            color: #fff;
        }

        .cancel {
            background-color: #555;
            color: #fff;
        }

        .message {
            color: red;
        }
    </style>
</head>

<body>
    <div class="container">
        <h1>⚠️ ยืนยันการลบสินค้า</h1>

        <?php if (isset($error)) echo "<p class='message'>$error</p>"; ?>

        <p>คุณแน่ใจหรือไม่ว่าต้องการลบสินค้า <b><?= htmlspecialchars($product['p_name']) ?></b>?</p>

        <img src="<?= htmlspecialchars($product['img_url']) ?>" alt="Product Image">

        <form method="post">
            <input type="hidden" name="confirm_delete" value="1">
            <button type="submit" class="btn confirm">ยืนยันการลบ</button>
            <a href="index.php"><button type="button" class="btn cancel">ยกเลิก</button></a>
            <!--<a href="admin_dashboard.php"><button type="button" class="btn cancel">ยกเลิก</button></a>-->
        </form>
    </div>
</body>
</html>
