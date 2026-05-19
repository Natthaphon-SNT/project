<?php
session_start();
include "db_conn.php";

if (!isset($_SESSION['cart']) || count($_SESSION['cart']) == 0) {
    echo "<h3 style='color:white; text-align:center;'>ยังไม่มีสินค้าในตะกร้า</h3>";
    echo "<p style='text-align:center;'><a href='index.php' style='color:cyan;'>กลับไปเลือกสินค้า</a></p>";
    exit; 
}
?>

<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>ตะกร้าสินค้า</title>
<style>
    body { background:#202020; color:#fff; font-family:Arial; }
    table { width:80%; margin:auto; border-collapse:collapse; }
    th, td { padding:10px; border:1px solid #666; text-align:center; }
    .btn { background:crimson; color:white; padding:10px 20px; border:none; cursor:pointer; margin-top:20px; }
    .btn:hover { background:red; }
    .del-btn { background:#444; color:white; padding:6px 12px; border:none; cursor:pointer; text-decoration: none; display: inline-block;}
    .del-btn:hover { background:#e60000; }
</style>
</head>
<body>

<h2 style="text-align:center;">🛒 ตะกร้าสินค้าของคุณ</h2>

<table>
    <tr>
        <th>รูป</th>
        <th>ชื่อสินค้า</th>
        <th>ราคา</th>
        <th>จำนวน</th>
        <th>ราคารวม</th>
        <th>ลบ</th>
    </tr>

    <?php
    $total = 0;
    
    foreach ($_SESSION['cart'] as $index => $item) {

        $is_promotion = isset($item['promo_id']);
        
        if ($is_promotion) {
            $item_id    = $item['promo_id'];
            $item_name  = $item['promo_name'];
            $item_price = $item['promo_price'];
            $item_img   = $item['promo_img'];
        } else {
          
            $item_id    = $item['product_id'];
            $item_name  = $item['p_name'];
            $item_price = $item['p_price'];
            $item_img   = $item['img_url'];
        }
       

        $subtotal = floatval($item_price) * intval($item['quantity']);
        $total += $subtotal;
        
        echo "
        <tr>
            <td><img src='{$item_img}' width='80' alt='{$item_name}'></td>
            <td>{$item_name}</td>
            <td>฿" . number_format(floatval($item_price), 2) . "</td>
            <td>{$item['quantity']}</td>
            <td>฿" . number_format(floatval($subtotal), 2) . "</td>
            <td>
                <a href='remove.php?id={$item_id}' class='del-btn'>ลบ</a>
            </td>
        </tr>";
    }
    ?>
    
    <tr>
        <td colspan="4" style="text-align:right;">ยอดรวมทั้งหมด</td>
        <td colspan="2">฿<?php echo number_format($total, 2); ?></td>
    </tr>
</table>

<div style="text-align:center; align-items: center; margin-top: 20px;">
    <form action="checkout.php" method="post">
        <a href="index.php" style="margin: 0 50px; text-decoration: none; color: #ddd">⬅️ เลือกสินค้าต่อ</a>
        <input type="hidden" name="total" value="<?php echo $total; ?>">
        <button type="submit" class="btn">สั่งซื้อสินค้า</button>
    </form>
</div>

</body>
</html>