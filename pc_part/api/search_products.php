<?php
include "db_conn.php";

$search = $_GET['search'] ?? '';
$category = $_GET['category'] ?? '';

$sql = "SELECT * FROM products WHERE 1=1";

if (!empty($search)) {
    $search = $conn->real_escape_string($search);
    $sql .= " AND (p_name LIKE '%$search%' OR p_description LIKE '%$search%')";
}


if (!empty($category)) {
    $category = $conn->real_escape_string($category);
    $sql .= " AND cid = '$category'";
}

$sql .= " ORDER BY cid ASC";

$result = $conn->query($sql);
$products = [];

while ($row = $result->fetch_assoc()) {
    $products[] = $row;
}

header('Content-Type: application/json');
echo json_encode($products);
?>
