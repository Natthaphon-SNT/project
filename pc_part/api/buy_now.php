<?php
session_start();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {

    $product_id = $_POST['product_id'];
    $p_name = $_POST['p_name'];
    $p_price = $_POST['p_price'];
    $img_url = $_POST['img_url'];
    $quantity = (int)($_POST['quantity'] ?? 1); 

    if ($quantity <= 0) {
        $quantity = 1;
    }

    if (!isset($_SESSION['cart'])) {
        $_SESSION['cart'] = [];
    }

    if (isset($_SESSION['cart'][$product_id])) {
        $_SESSION['cart'][$product_id]['quantity'] += $quantity;
    } else {
        $_SESSION['cart'][$product_id] = [
            'product_id' => $product_id,
            'p_name'     => $p_name,
            'p_price'    => $p_price,
            'img_url'    => $img_url,
            'quantity'   => $quantity
        ];
    }

    $total = 0;
    foreach ($_SESSION['cart'] as $item) {
        $total += $item['p_price'] * $item['quantity'];
    }

    header("Location: checkout.php?total=" . $total);
    exit;

} else {
    header("Location: index.php");
    exit;
}
?>
