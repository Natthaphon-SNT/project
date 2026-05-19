<?php
session_start();
require 'db_conn.php';

ini_set('display_errors', 1);
error_reporting(E_ALL);

if (!isset($_SESSION['u_name']) || $_SESSION['u_role'] !== 'admin') {
    header("Location: login.php");
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $promo_id = trim($_POST['promo_id']) ?? '';
    $promo_name = trim($_POST['promo_name'] ?? '');
    $promo_description = trim($_POST['promo_description'] ?? '');
    $discount_type = trim($_POST['discount_type'] ?? '');
    $discount_value = trim($_POST['discount_value'] ?? '');
    $promo_stock = (int)($_POST['promo_stock'] ?? 0);
    $start_date = trim($_POST['start_date'] ?? '');
    $end_date = trim($_POST['end_date'] ?? '');
    $status = trim($_POST['status'] ?? '');
    $promo_price = trim($_POST['promo_price'] ?? '');
    $promo_img = trim($_POST['promo_img'] ?? '');

    
    if ($promo_id === '' || $promo_name === '' || $discount_type === '' || $discount_value === '' || $promo_stock === '' ||
        $start_date === '' || $end_date === '' || $status === '' || $promo_price === '') {
        $error = "⚠️ กรุณากรอกข้อมูลให้ครบถ้วน (ยกเว้นรูปภาพและคำอธิบาย)";
    } elseif (!is_numeric($discount_value) || $discount_value <= 0) {
        $error = "⚠️ ส่วนลดต้องเป็นตัวเลขและมากกว่า 0";
    } elseif (!is_numeric($promo_price) || $promo_price <= 0) {
        $error = "⚠️ ราคาโปรโมชั่นต้องเป็นตัวเลขและมากกว่า 0";
    } elseif (!is_numeric($promo_stock) || $promo_stock < 0) {
        $error = "⚠️ สต็อกต้องเป็นตัวเลข 0 หรือมากกว่า";
    } else {
        
        $stmt = $conn->prepare("INSERT INTO promotions 
            (promo_id, promo_name, promo_description, discount_type, discount_value, promo_stock, start_date, end_date, status, promo_price, promo_img)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
        $stmt->bind_param(
            "ssssissssss",
            $promo_id,
            $promo_name,
            $promo_description,
            $discount_type,
            $discount_value,
            $promo_stock,
            $start_date,
            $end_date,
            $status,
            $promo_price,
            $promo_img
        );

        if ($stmt->execute()) {
            $success = "✅ เพิ่มโปรโมชั่นใหม่เรียบร้อยแล้ว!";
        } else {
            $error = "❌ เกิดข้อผิดพลาดในการเพิ่มโปรโมชั่น: " . $stmt->error;
        }

        $stmt->close();
    }
}
?>

<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>เพิ่มโปรโมชั่นใหม่</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #202020ff 0%, #000000ff 100%);
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 600px;
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

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 15px;
            text-align: left;
            align-items: center;
        }

        .form-grid label {
            font-weight: 600;
            text-align: right;
            padding-right: 10px;
        }

        input[type="text"],
        input[type="number"],
        input[type="date"],
        textarea,
        select {
            color: #fff;
            width: 95%;
            padding: 8px;
            margin: 5px 0;
            font-size: 16px;
            border: 1px solid #555;
            border-radius: 6px;
            box-sizing: border-box;
            background-color: #333;
        }

        textarea {
            height: 100px;
            resize: vertical;
        }

        input[type="submit"], button {
            width: 150px;
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
            margin-top: 30px;
            grid-column: 1 / -1;
        }

        p.message {
            color: red;
            font-weight: bold;
        }

        p.success {
            color: green;
            font-weight: bold;
        }

        img.preview {
            max-width: 250px;
            border-radius: 8px;
            margin-top: 10px;
            border: 1px solid #ddd;
        }

        label {
            color: #fff;
        }

        .full-width {
            grid-column: 1 / -1;
            text-align: center;
        }
    </style>
</head>

<body>
    <div class="container">
        <h1>เพิ่มโปรโมชั่นใหม่</h1>

        <?php 
        if (isset($error)) echo "<p class='message'>$error</p>"; 
        if (isset($success)) echo "<p class='success'>$success</p>"; 
        ?>

        <form method="post">
            <div class="form-grid">
                <label>รหัสโปรโมชัน: </label>
                <input type="text" id="promo_id" name="promo_id" required>

                <label for="promo_name">ชื่อโปรโมชั่น:</label>
                <input type="text" id="promo_name" name="promo_name" required>

                <label for="promo_price">ราคาโปรโมชั่น:</label>
                <input type="number" id="promo_price" step="0.01" name="promo_price" required>

                <label for="discount_type">ประเภทส่วนลด:</label>
                <select id="discount_type" name="discount_type" required>
                    <option value="">-- เลือกประเภทส่วนลด --</option>
                    <option value="percent">Percent (%)</option>
                    <option value="fixed">Fixed (บาท)</option>
                </select>

                <label for="discount_value">มูลค่าส่วนลด:</label>
                <input type="number" id="discount_value" step="0.01" name="discount_value" required>

                <label for="promo_stock">สต็อก:</label>
                <input type="number" id="promo_stock" name="promo_stock" required>

                <label for="start_date">วันที่เริ่ม:</label>
                <input type="date" id="start_date" name="start_date" required>

                <label for="end_date">วันที่สิ้นสุด:</label>
                <input type="date" id="end_date" name="end_date" required>

                <label for="status">สถานะ:</label>
                <select id="status" name="status" required>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                </select>

                <label for="promo_description">รายละเอียด:</label>
                <textarea id="promo_description" name="promo_description"></textarea>

                <label for="promo_img">ลิงก์รูปภาพ:</label>
                <input type="text" id="promo_img" name="promo_img">

                <div class="form-action">
                    <input type="submit" value="บันทึกโปรโมชั่น">
                    <a href="index.php"><button type="button">กลับ</button></a>
                </div>
            </div>
        </form>
    </div>
</body>
</html>
