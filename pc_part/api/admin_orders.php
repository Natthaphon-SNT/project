<?php
session_start();
require 'db_conn.php';

if (!isset($_SESSION['u_role']) || $_SESSION['u_role'] !== 'admin') {
    die("<p style='color:red;'>⛔ คุณไม่มีสิทธิ์เข้าหน้านี้</p>");
}

$sql = "
SELECT 
    o.order_id,
    o.order_date,
    o.payment_method,
    o.total_price,
    u.uid,
    u.u_name,
    u.u_email,
    u.u_phone
FROM orders o
JOIN users u ON o.uid = u.uid
ORDER BY o.order_date DESC
";

$orders = $conn->query($sql);
?>

<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>📊 รายงานคำสั่งซื้อทั้งหมด</title>
<link rel="stylesheet" href="src.css">
<style>
body {
    font-family: 'Segoe UI', Tahoma;
    background-color: #202020ff;
    margin: 0;
    padding: 0;
}
.container {
    max-width: 1200px;
    margin: 40px auto;
    background: #fff;
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}
h1 {
    text-align: center;
    color: #333;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}
th, td {
    border: 1px solid #ccc;
    padding: 10px;
    text-align: center;
}
th {
    background-color: #f3f4f6;
}
.details {
    background-color: #f9fafb;
    border-radius: 10px;
    padding: 10px;
}
.btn {
    background-color: #202020ff;
    border: 2px solid crimson;
    color: #fff;
    border: none;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
}
.btn:hover {
    background-color: #ff0000ff;
}
</style>
</head>
<body>
<div class="container">
    <h1>📦 รายการคำสั่งซื้อทั้งหมด</h1>

    <?php if ($orders->num_rows > 0): ?>
    <table>
        <tr>
            <th>รหัสคำสั่งซื้อ</th>
            <th>ชื่อผู้ซื้อ</th>
            <th>อีเมล</th>
            <th>เบอร์โทร</th>
            <th>วันที่สั่งซื้อ</th>
            <th>วิธีชำระเงิน</th>
            <th>ราคารวม (บาท)</th>
            <th>รายละเอียดสินค้า</th>
        </tr>

        <?php while($order = $orders->fetch_assoc()): ?>
        <tr>
            <td><?= htmlspecialchars($order['order_id']) ?></td>
            <td><?= htmlspecialchars($order['u_name']) ?></td>
            <td><?= htmlspecialchars($order['u_email']) ?></td>
            <td><?= htmlspecialchars($order['u_phone']) ?></td>
            <td><?= htmlspecialchars($order['order_date']) ?></td>
            <td><?= htmlspecialchars($order['payment_method']) ?></td>
            <td><?= number_format($order['total_price'], 2) ?></td>
            <td>
                <form method="get" action="order_detail.php">
                    <input type="hidden" name="order_id" value="<?= $order['order_id'] ?>">
                    <button class="btn" type="submit">ดูรายละเอียด</button>
                </form>
            </td>
        </tr>
        <?php endwhile; ?>
    </table>
    <br>
    <a href="index.php" style="margin-left: 800px; "><button style="background-color: #202020ff; border: 2px solid crimson;">Back</button></a>
    <?php else: ?>
        <p style="text-align:center;">❌ ยังไม่มีคำสั่งซื้อในระบบ</p>
    <?php endif; ?>
</div>
</body>
</html>
