<?php
require 'db_conn.php';

$sql = "SELECT * FROM categories";
$result = $conn->query($sql);

$categories = [];
while($row = $result->fetch_assoc()) {
    $categories[] = $row;
}

header("Content-Type: application/json");
echo json_encode($categories);
?>
