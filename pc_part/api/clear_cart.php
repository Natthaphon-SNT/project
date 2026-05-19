<?php
session_start();
unset($_SESSION['cart']);
echo 'ตะกร้าล้างแล้ว! <a href="index.php">กลับหน้าแรก</a>';
?>