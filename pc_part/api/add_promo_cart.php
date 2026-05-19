<?php
session_start();
include "db_conn.php"; 

if (!isset($_POST['promo_id'])) {
    die("<p style='color:white; text-align:center;'>❌ เกิดข้อผิดพลาด: ไม่พบข้อมูลโปรโมชั่น</p>");
}

$promo_id    = $_POST['promo_id'];
$promo_name  = $_POST['promo_name'];
$promo_price = $_POST['promo_price']; 
$promo_img   = $_POST['promo_img'];  
$quantity    = (int)$_POST['quantity']; 

if ($quantity <= 0) {
    $quantity = 1; 
}

if (isset($_SESSION['cart'][$promo_id])) {
    $_SESSION['cart'][$promo_id]['quantity'] += $quantity;
} else {
    $_SESSION['cart'][$promo_id] = [
        'promo_id'    => $promo_id,
        'promo_name'  => $promo_name,
        'promo_price' => $promo_price,
        'promo_img'   => $promo_img, 
        'quantity'    => $quantity
    ];
}

header("Location: viewcart.php");
exit;
?>