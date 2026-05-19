<?php
session_start();
require 'db_conn.php';

ini_set('display_errors', 1);
error_reporting(E_ALL);

if (!isset($_SESSION['u_role']) || $_SESSION['u_role'] !== 'admin') {
    die("<p style='color:red;'>⛔ คุณไม่มีสิทธิ์ในการลบโปรโมชั่น</p>");
}

if (!isset($_POST['promo_id'])) {
    die("<p style='color:red;'>❌ ไม่พบรหัสโปรโมชั่นที่ต้องการลบ</p>");
}

$promo_id = $_POST['promo_id'];

$stmt = $conn->prepare("SELECT promo_img FROM promotions WHERE promo_id = ?");
$stmt->bind_param("s", $promo_id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows === 0) {
    die("<p style='color:red;'>❌ ไม่พบโปรโมชั่นนี้ในฐานข้อมูล</p>");
}

$promo = $result->fetch_assoc();
$stmt->close();

if (!empty($promo['promo_img']) && file_exists($promo['promo_img'])) {
    unlink($promo['promo_img']);
}

$delete = $conn->prepare("DELETE FROM promotions WHERE promo_id = ?");
$delete->bind_param("s", $promo_id);

if ($delete->execute()) {
    echo "<script>alert('✅ ลบโปรโมชั่นเรียบร้อยแล้ว'); window.location.href='index.php';</script>";
} else {
    echo "<p style='color:red;'>❌ ลบโปรโมชั่นไม่สำเร็จ: " . $delete->error . "</p>";
}

$delete->close();
$conn->close();
?>
