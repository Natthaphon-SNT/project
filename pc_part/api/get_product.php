<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");

include '../db_conn.php';

$category = isset($_GET['category']) ? mysqli_real_escape_string($conn, $_GET['category']) : '';
$search = isset($_GET['search']) ? mysqli_real_escape_string($conn, $_GET['search']) : '';

// สร้าง Query พื้นฐาน
$sql = "SELECT * FROM products WHERE 1=1";

if (!empty($category)) {
    $sql .= " AND category = '$category'";
}
if (!empty($search)) {
    $sql .= " AND (name LIKE '%$search%' OR description LIKE '%$search%')";
}

$result = mysqli_query($conn, $sql);
$products = array();

while($row = mysqli_fetch_assoc($result)) {
    $products[] = $row;
}

echo json_encode(["status" => "success", "data" => $products]);
?>