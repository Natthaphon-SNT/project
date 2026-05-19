<?php
// cron_update_prices.php (รันทุกวัน เช่า 02:00 น.)

include 'db_conn.php';

// ดึงสินค้าทั้งหมดจากฐานข้อมูล
function fetchFromDB($conn) {
    $sql = "SELECT product_id, p_name FROM products";
    $result = $conn->query($sql);
    
    if (!$result) {
        die("Query Error: " . $conn->error);
    }
    
    $products = [];
    while ($row = $result->fetch_assoc()) {
        $products[] = $row;
    }
    return $products;
}

// ดึงราคาจาก JIB (ตัวอย่าง - ต้องปรับให้ใช้ได้จริง)
function scrapeJibPrice($productName) {
    try {
        // ตัวอย่าง: ใช้ cURL หรือ API
        $encodedName = urlencode($productName);
        $url = "https://jib.co.th/search/" . $encodedName;
        
        // ถ้ามี API ให้ใช้แทน
        // $url = "https://api.jib.co.th/products?q=" . $encodedName;
        
        // หลักการ scrape (ต้องตั้งค่า เพื่อ production)
        // $ch = curl_init($url);
        // curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        // $response = curl_exec($ch);
        // curl_close($ch);
        
        // Placeholder
        return 0;
        
    } catch (Exception $e) {
        error_log("Scrape Error: " . $e->getMessage());
        return 0;
    }
}

// อัปเดตราคาในฐานข้อมูล
function updatePrice($conn, $productId, $price) {
    if ($price <= 0) {
        error_log("Invalid price for product_id: $productId");
        return false;
    }
    
    $sql = "UPDATE products SET p_price = ? WHERE product_id = ?";
    $stmt = $conn->prepare($sql);
    
    if (!$stmt) {
        error_log("Prepare Error: " . $conn->error);
        return false;
    }
    
    $stmt->bind_param("di", $price, $productId);
    $result = $stmt->execute();
    $stmt->close();
    
    return $result;
}

// Main Logic
try {
    $products = fetchFromDB($conn);
    echo "กำลังอัปเดตราคา " . count($products) . " สินค้า...\n";
    
    $updated = 0;
    foreach ($products as $p) {
        $price = scrapeJibPrice($p['p_name']);
        if (updatePrice($conn, $p['product_id'], $price)) {
            $updated++;
        }
    }
    
    echo "อัปเดตสำเร็จ: $updated รายการ\n";
    
} catch (Exception $e) {
    echo "Error: " . $e->getMessage();
} finally {
    $conn->close();
}
?>