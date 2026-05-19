<?php
// 1. อนุญาตให้ Angular เข้าถึงได้
header("Access-Control-Allow-Origin: *"); 
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With");

// ดักจับ Preflight Request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// 2. บอกว่าไฟล์นี้จะตอบกลับเป็น JSON
header("Content-Type: application/json; charset=UTF-8");

include '../db_conn.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    
    // 3. รับข้อมูลแบบ JSON ที่ Angular ส่งมา
    $data = json_decode(file_get_contents("php://input"));

    // เช็คว่ามีค่าส่งมาหรือไม่ (รองรับทั้งตัวแปรชื่อ email และ u_name เผื่อตั้งชื่อใน Angular ไม่ตรง)
    $username = isset($data->email) ? $data->email : (isset($data->u_name) ? $data->u_name : '');
    $password = isset($data->password) ? $data->password : (isset($data->u_password) ? $data->u_password : '');

    if (empty($username) || empty($password)) {
        echo json_encode(["status" => "error", "message" => "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน"]);
        exit;
    } 

    $sql = "SELECT * FROM users WHERE u_name = ? LIMIT 1";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $username);
    $stmt->execute();
    $res = $stmt->get_result();

    if ($res->num_rows === 1) {
        $row = $res->fetch_assoc();
        $row['u_password'] = trim($row['u_password']);
        
        if (password_verify($password, $row['u_password'])) {
            // 4. ห้ามใช้ header("Location...") ให้ส่งเป็น JSON แทน
            echo json_encode([
                "status" => "success",
                "message" => "เข้าสู่ระบบสำเร็จ",
                "user" => [
                    "id" => $row['uid'],
                    "name" => $row['u_name'],
                    "role" => $row['u_role']
                ]
            ]);
        } else {
            echo json_encode(["status" => "error", "message" => "รหัสผ่านไม่ถูกต้อง"]);
        }
    } else {
        echo json_encode(["status" => "error", "message" => "ไม่พบบัญชีนี้"]);
    }
}
?>