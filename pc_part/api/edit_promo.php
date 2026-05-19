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
    die("<p style='color:red'>❌ ไม่พบรหัสโปรโมชั่นที่ต้องการแก้ไข</p>");
}

$promo_id = $_GET['id'];

$stmt = $conn->prepare("SELECT * FROM promotions WHERE promo_id = ? LIMIT 1");
$stmt->bind_param("s", $promo_id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows === 0) {
    die("<p style='color:red'>❌ ไม่พบโปรโมชั่นนี้ในระบบ</p>");
}

$promotion = $result->fetch_assoc();
$stmt->close();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
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

    if ($promo_name === '' || $discount_type === '' || $discount_value === '' || $promo_stock === '' || $start_date === '' || $end_date === '' || $status === '' || $promo_price === '') {
        $error = "⚠️ กรุณากรอกข้อมูลให้ครบถ้วน (ยกเว้นรูปภาพและคำอธิบาย)";
    } elseif (!is_numeric($discount_value) || $discount_value <= 0) {
        $error = "⚠️ ส่วนลดต้องเป็นตัวเลขและมากกว่า 0";
    } elseif (!is_numeric($promo_price) || $promo_price <= 0) {
        $error = "⚠️ ราคาโปรโมชั่นต้องเป็นตัวเลขและมากกว่า 0";
    } elseif (!is_numeric($promo_stock) || $promo_stock < 0) {
        $error = "⚠️ สต็อกต้องเป็นตัวเลข 0 หรือมากกว่า";
    } else {
        
        $update = $conn->prepare("UPDATE promotions 
                                 SET promo_name = ?, promo_description = ?, discount_type = ?, 
                                     discount_value = ?, promo_stock = ?, start_date = ?, 
                                     end_date = ?, status = ?, promo_price = ?, 
                                     promo_img = ?
                                 WHERE promo_id = ?");
        
        $update->bind_param(
            "ssssissssss",
            $promo_name,
            $promo_description,
            $discount_type,
            $discount_value,
            $promo_stock,
            $start_date,
            $end_date,
            $status,
            $promo_price,
            $promo_img,
            $promo_id
        );

        if ($update->execute()) {
            $success = "✅ แก้ไขข้อมูลโปรโมชั่นเรียบร้อยแล้ว";
            $promotion = [
                'promo_name' => $promo_name,
                'promo_description' => $promo_description,
                'discount_type' => $discount_type,
                'discount_value' => $discount_value,
                'promo_stock' => $promo_stock,
                'start_date' => $start_date,
                'end_date' => $end_date,
                'status' => $status,
                'promo_price' => $promo_price,
                'promo_img' => $promo_img,
            ];
        } else {
            $error = "❌ ไม่สามารถแก้ไขโปรโมชั่นได้: " . $update->error;
        }
        $update->close();
    }
}
?>

<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>แก้ไขโปรโมชั่น</title>
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
        <h1>แก้ไขโปรโมชั่น: <?= htmlspecialchars($promo_id) ?></h1>

        <?php 
        if (isset($error)) echo "<p class='message'>$error</p>"; 
        if (isset($success)) echo "<p class='success'>$success</p>"; 
        ?>

        <form method="post">
            <div class="form-grid">
                <label for="promo_name">ชื่อโปรโมชั่น:</label>
                <input type="text" id="promo_name" name="promo_name" value="<?= htmlspecialchars($promotion['promo_name']) ?>">

                <label for="promo_price">ราคาโปรโมชั่น:</label>
                <input type="number" id="promo_price" step="0.01" name="promo_price" value="<?= htmlspecialchars($promotion['promo_price']) ?>">

                <label for="discount_type">ประเภทส่วนลด:</label>
                <select id="discount_type" name="discount_type">
                    <option value="percent" <?= ($promotion['discount_type'] == 'percent') ? 'selected' : '' ?>>Percent (%)</option>
                    <option value="fixed" <?= ($promotion['discount_type'] == 'fixed') ? 'selected' : '' ?>>Fixed (บาท)</option>
                </select>

                <label for="discount_value">มูลค่าส่วนลด:</label>
                <input type="number" id="discount_value" step="0.01" name="discount_value" value="<?= htmlspecialchars($promotion['discount_value']) ?>">

                <label for="promo_stock">สต็อก:</label>
                <input type="number" id="promo_stock" name="promo_stock" value="<?= htmlspecialchars($promotion['promo_stock']) ?>">

                <label for="start_date">วันที่เริ่ม:</label>
                <input type="date" id="start_date" name="start_date" value="<?= htmlspecialchars($promotion['start_date']) ?>">

                <label for="end_date">วันที่สิ้นสุด:</label>
                <input type="date" id="end_date" name="end_date" value="<?= htmlspecialchars($promotion['end_date']) ?>">

                <label for="status">สถานะ:</label>
                <select id="status" name="status">
                    <option value="active" <?= ($promotion['status'] == 'active') ? 'selected' : '' ?>>Active</option>
                    <option value="inactive" <?= ($promotion['status'] == 'inactive') ? 'selected' : '' ?>>Inactive</option>
                    <option value="expired" <?= ($promotion['status'] == 'expired') ? 'selected' : '' ?>>Expired</option>
                </select>

                <label for="promo_description">รายละเอียด:</label>
                <textarea id="promo_description" name="promo_description"><?= htmlspecialchars($promotion['promo_description']) ?></textarea>

                <label for="promo_img">ลิงก์รูปภาพ:</label>
                <input type="text" id="promo_img" name="promo_img" value="<?= htmlspecialchars($promotion['promo_img']) ?>">

                <?php if (!empty($promotion['promo_img'])): ?>
                    <div class="full-width">
                        <img src="<?= htmlspecialchars($promotion['promo_img']) ?>" alt="Promotion Image" class="preview">
                    </div>
                <?php endif; ?>

                <div class="form-action">
                    <input type="submit" value="บันทึกการแก้ไข">
                    <a href="index.php"><button type="button">กลับ</button></a> 
                    </div>
            </div>
        </form>
    </div>
</body>
</html>