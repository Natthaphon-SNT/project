<?php
session_start();
include "db_conn.php";

if (!isset($_GET['id'])) {
    die("❌ ไม่พบรหัสสินค้า");
}

$product_id = $_GET['id'];
$uid = $_SESSION['uid'] ?? null;

if (!$uid) {
    die("❌ ไม่พบผู้ใช้งาน");
}

// ✅ ลบจาก SESSION
foreach ($_SESSION['cart'] as $key => $item) {
    if ($item['product_id'] == $product_id) {
        unset($_SESSION['cart'][$key]);
        break;
    }
}
// รีเซ็ต index array
$_SESSION['cart'] = array_values($_SESSION['cart']);

// ✅ ลบจาก DATABASE (ถ้ามีข้อมูลในตาราง cart_item)
$cart_query = $conn->prepare("SELECT cart_id FROM cart WHERE uid = ?");
$cart_query->bind_param("s", $uid);
$cart_query->execute();
$result = $cart_query->get_result();
$cart = $result->fetch_assoc();

if ($cart) {
    $cart_id = $cart['cart_id'];
    $stmt = $conn->prepare("DELETE FROM cart_item WHERE cart_id = ? AND product_id = ?");
    $stmt->bind_param("ss", $cart_id, $product_id);
    $stmt->execute();
}

header("Location: viewcart.php");
exit;
?>
