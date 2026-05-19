<?php
session_start();
include "db_conn.php"; 

$uid = (string) ($_POST['uid'] ?? ($_SESSION['uid'] ?? '0'));
$u_name = trim($_POST['u_name'] ?? ($_SESSION['u_name'] ?? 'ลูกค้าทั่วไป'));
$payment_method = $_POST['payment_method'] ?? 'N/A';
$total_price_post = $_POST['total_price'] ?? 0;

$cart_items = $_SESSION['cart'] ?? [];

$total_amount = 0;
$total_price = 0;
foreach($cart_items as $item){
    $is_promotion = isset($item['promo_id']);
    $item_price = $is_promotion ? $item['promo_price'] : $item['p_price'];
    $total_amount += $item['quantity'];
    $total_price += floatval($item_price) * intval($item['quantity']);
}

$order_status = "paid"; 

$stmt_order = $conn->prepare("
    INSERT INTO orders (uid, order_date, payment_method, total_amount, total_price, o_status)
    VALUES (?, NOW(), ?, ?, ?, ?)
");
$stmt_order->bind_param("ssids", $uid, $payment_method, $total_amount, $total_price, $order_status);
$stmt_order->execute();
$order_id = $stmt_order->insert_id;
$stmt_order->close();

if(!empty($cart_items)) {
    $stmt_item = $conn->prepare("
        INSERT INTO order_items (order_id, product_id, oi_quantity, oi_price)
        VALUES (?, ?, ?, ?)
    ");
    
    foreach($cart_items as $item){
        $is_promotion = isset($item['promo_id']);
        $item_id_to_save = $is_promotion ? $item['promo_id'] : $item['product_id'];
        $item_price_to_save = $is_promotion ? $item['promo_price'] : $item['p_price'];
        $stmt_item->bind_param("isid", $order_id, $item_id_to_save, $item['quantity'], $item_price_to_save);
        $stmt_item->execute();
    }
    $stmt_item->close();
}

unset($_SESSION['cart']);
?>

<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>การชำระเงินสำเร็จ</title>
<style>
    body {
        background: #202020; color: #fff; font-family: Arial, sans-serif;
        display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0;
    }
    .container {
        background: #2b2b2b; padding: 40px; border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.6); max-width: 700px; width: 90%; text-align: center;
    }
    h1 { color: #00e676; font-size: 32px; margin-bottom: 20px; text-shadow: 1px 1px 4px rgba(0,0,0,0.6); }
    h2 { margin-top: 30px; margin-bottom: 15px; font-size: 24px; color: #ff6b6b; }
    p { font-size: 18px; margin-bottom: 15px; }
    table { margin: 20px auto; border-collapse: collapse; width: 100%; }
    th, td { padding: 10px; border: 1px solid #fff; text-align: center; }
    a {
        display: inline-block; margin-top: 20px; padding: 12px 25px; background: crimson;
        color: #fff; border-radius: 10px; text-decoration: none; font-size: 18px; transition: 0.3s;
    }
    a:hover { background: #ff4c4c; }
</style>
</head>
<body>

<div class="container">
    <h1>✅ การชำระเงินสำเร็จ!</h1>
    <p>ขอบคุณคุณ <b><?php echo htmlspecialchars($u_name, ENT_QUOTES); ?></b> ที่ใช้บริการของเรา ❤️</p>
    <p>วิธีชำระเงิน: <b><?php echo htmlspecialchars($payment_method, ENT_QUOTES); ?></b></p>
    <p>จำนวนสินค้า: <b><?php echo $total_amount; ?></b> ชิ้น</p>
    <p>ยอดรวมทั้งหมด: <b>฿<?php echo number_format($total_price, 2); ?></b></p>

    <h2>รายละเอียดสินค้า</h2>
    <table>
        <tr>
            <th>ชื่อสินค้า</th>
            <th>ราคา/ชิ้น</th>
            <th>จำนวน</th>
            <th>รวม</th>
        </tr>
    <?php
    foreach($cart_items as $item){
        $is_promotion = isset($item['promo_id']);
        $item_name  = $is_promotion ? $item['promo_name'] : $item['p_name'];
        $item_price = $is_promotion ? $item['promo_price'] : $item['p_price'];
        $subtotal = floatval($item_price) * intval($item['quantity']);
        
        echo "<tr>
            <td>".htmlspecialchars($item_name)."</td>
            <td>฿".number_format($item_price, 2)."</td>
            <td>{$item['quantity']}</td>
            <td>฿".number_format($subtotal, 2)."</td>
        </tr>";
    }
    ?>
    </table>

    <p style="color:#00e676; font-size:20px;">สถานะคำสั่งซื้อ: <b>ชำระเงินเรียบร้อยแล้ว</b></p>

    <a href="index.php">กลับไปหน้าแรก</a>
</div>

</body>
</html>
