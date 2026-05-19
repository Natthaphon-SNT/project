<?php
session_start();

$payment = $_POST['payment_method'] ?? '';
$total = $_POST['total'] ?? 0;
$address = $_POST['address'] ?? '';
$fullname = $_POST['fullname'] ?? 'ไม่ระบุ';
$phone = $_POST['phone'] ?? '-';
$cart = $_SESSION['cart'] ?? [];

?>
<!DOCTYPE html>
<html lang="th">

<head>
    <meta charset="UTF-8">
    <title>สถานะคำสั่งซื้อ</title>
    <style>
        body {
            background: #202020;
            color: #fff;
            font-family: Arial;
            padding: 30px;
        }

        .container {
            background: #2b2b2b;
            padding: 30px;
            border-radius: 15px;
            max-width: 600px;
            margin: auto;
        }

        h2 {
            color: lime;
        }

        ul {
            list-style: none;
            padding: 0;
        }

        li {
            margin: 5px 0;
        }

        .status {
            margin-top: 20px;
            padding: 10px;
            background: #333;
            border-radius: 10px;
            text-align: center;
        }
    </style>
</head>

<body>
    <div class="container">
        <h2>📦 สถานะคำสั่งซื้อ</h2>
        <p>ชำระโดย: <b><?php echo htmlspecialchars($payment); ?></b></p>
        <p>ยอดรวม: <b>฿<?php echo number_format($total); ?></b></p>

        <h3>รายละเอียดผู้สั่งซื้อ</h3>
        <ul>
            <li>ชื่อ: <?php echo htmlspecialchars($fullname); ?></li>
            <li>เบอร์: <?php echo htmlspecialchars($phone); ?></li>
            <li>ที่อยู่: <?php echo htmlspecialchars($address); ?></li>
        </ul>

        <h3>รายการสินค้า</h3>
        <ul>
            <?php foreach ($cart as $item): ?>
                <li><?php echo $item['name']; ?> × <?php echo $item['qty']; ?> — ฿<?php echo number_format($item['price']); ?></li>
            <?php endforeach; ?>
        </ul>

        <div class="status">
            🚚 <b>สถานะ: กำลังจัดส่ง</b><br>
            หมายเลขพัสดุ: TH<?php echo rand(1000000, 9999999); ?>
        </div>
    </div>
</body>

</html>