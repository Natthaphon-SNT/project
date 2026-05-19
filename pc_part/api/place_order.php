<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Methods: POST");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

include '../db_conn.php';

// รับค่า JSON จาก Angular
$data = json_decode(file_get_contents("php://input"));

if(isset($data->customer) && isset($data->items)) {
    $name = mysqli_real_escape_string($conn, $data->customer->name);
    $phone = mysqli_real_escape_string($conn, $data->customer->phone);
    $address = mysqli_real_escape_string($conn, $data->customer->address);
    $total_price = (float)$data->total_price;
    $order_date = date('Y-m-d H:i:s');

    // 1. Insert ลงตาราง orders
    $sql_order = "INSERT INTO orders (customer_name, phone, address, total_price, order_date, status) 
                  VALUES ('$name', '$phone', '$address', '$total_price', '$order_date', 'pending')";
    
    if(mysqli_query($conn, $sql_order)) {
        $order_id = mysqli_insert_id($conn); // ดึง ID ล่าสุดที่เพิ่ง insert

        // 2. Loop วน Insert สินค้าลงตาราง order_details (สมมติว่าคุณมีตารางนี้)
        foreach($data->items as $item) {
            $product_id = (int)$item->id;
            $qty = (int)$item->quantity;
            $price = (float)$item->price;

            $sql_detail = "INSERT INTO order_details (order_id, product_id, quantity, price) 
                           VALUES ('$order_id', '$product_id', '$qty', '$price')";
            mysqli_query($conn, $sql_detail);
        }

        echo json_encode(["status" => "success", "message" => "Order placed successfully"]);
    } else {
        echo json_encode(["status" => "error", "message" => mysqli_error($conn)]);
    }
} else {
    echo json_encode(["status" => "error", "message" => "Invalid data"]);
}
?>