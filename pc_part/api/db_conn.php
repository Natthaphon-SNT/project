<?php
$servername = "localhost";
$username = "root";  
$password = "";
$dbname = "diy";

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    die("เชื่อมต่อฐานข้อมูลล้มเหลว: " . $conn->connect_error);
}
?>
