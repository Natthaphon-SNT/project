<?php
session_start();
require 'db_conn.php';

if (!isset($_GET['order_id'])) {
    die("<p style='color:red;'>❌ ไม่พบรหัสคำสั่งซื้อ</p>");
}

$order_id = $_GET['order_id'];

$order_sql = "
SELECT o.*, u.u_name, u.u_email, u.u_phone
FROM orders o
JOIN users u ON o.uid = u.uid
WHERE o.order_id = ?
";
$stmt = $conn->prepare($order_sql);
$stmt->bind_param("i", $order_id);
$stmt->execute();
$order = $stmt->get_result()->fetch_assoc();

$items_sql = "
SELECT oi.*, p.p_name, p.p_price
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
WHERE oi.order_id = ?
";
$stmt2 = $conn->prepare($items_sql);
$stmt2->bind_param("i", $order_id);
$stmt2->execute();
$items = $stmt2->get_result();
?>

<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>รายละเอียดคำสั่งซื้อ #<?= htmlspecialchars($order_id) ?></title>
<style>
body {
    font-family: 'Segoe UI', Tahoma;
    background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
}
.container {
    max-width: 800px;
    margin: 40px auto;
    background: #fff;
    padding: 30px;
    border-radius: 16px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
h2 { color: #333; }
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}
th, td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: center;
}
th {
    background: #f3f4f6;
}
</style>
</head>
<body>
<div class="container">
    <h2>รายละเอียดคำสั่งซื้อ #<?= htmlspecialchars($order['order_id']) ?></h2>
    <p><b>ชื่อผู้ซื้อ:</b> <?= htmlspecialchars($order['u_name']) ?></p>
    <p><b>อีเมล:</b> <?= htmlspecialchars($order['u_email']) ?></p>
    <p><b>เบอร์โทร:</b> <?= htmlspecialchars($order['u_phone']) ?></p>
    <p><b>วันที่สั่งซื้อ:</b> <?= htmlspecialchars($order['order_date']) ?></p>
    <p><b>วิธีชำระเงิน:</b> <?= htmlspecialchars($order['payment_method']) ?></p>

    <h3>สินค้าในคำสั่งซื้อนี้</h3>
    <table>
        <tr>
            <th>ชื่อสินค้า</th>
            <th>จำนวน</th>
            <th>ราคาต่อชิ้น</th>
            <th>ราคารวม</th>
        </tr>
        <?php 
        $grand_total = 0;
        while($item = $items->fetch_assoc()):
            $subtotal = $item['oi_quantity'] * $item['oi_price']; 
            $grand_total += $subtotal;
        ?>
        <tr>
            <td><?= htmlspecialchars($item['p_name']) ?></td>
            <td><?= htmlspecialchars($item['oi_quantity']) ?></td>
            <td><?= number_format($item['p_price'], 2) ?></td>
            <td><?= number_format($subtotal, 2) ?></td>
        </tr>
        <?php endwhile; ?>
    </table>

    <h3 style="text-align:right;">💰 รวมทั้งหมด: <?= number_format($grand_total, 2) ?> บาท</h3>

    <p style="text-align:center;"><a href="admin_orders.php">⬅ กลับหน้ารายการคำสั่งซื้อ</a></p>
</div>
</body>
</html>
