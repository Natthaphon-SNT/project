<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");

include '../db_conn.php';

$id = isset($_GET['id']) ? (int)$_GET['id'] : 0;

$sql = "SELECT * FROM products WHERE id = $id";
$result = mysqli_query($conn, $sql);

if(mysqli_num_rows($result) > 0) {
    $product = mysqli_fetch_assoc($result);
    echo json_encode(["status" => "success", "data" => $product]);
} else {
    echo json_encode(["status" => "error", "message" => "ไม่พบสินค้านี้"]);
}
?>