<?php
session_start();
include "db_conn.php";

if (!isset($_GET['id'])) {
    die("<p style='color:white; text-align:center;'>❌ ไม่พบโปรโมชั่นที่เลือก</p>");
}

$id = $_GET['id'];

$stmt = $conn->prepare("SELECT * FROM promotions WHERE promo_id = ?");
$stmt->bind_param("s", $id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows == 0) {
    die("<p style='color:white; text-align:center;'>❌ ไม่พบโปรโมชั่นนี้ในฐานข้อมูล</p>");
}

$promo = $result->fetch_assoc();
?>

<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title><?php echo htmlspecialchars($promo['promo_name']); ?></title>
<link rel="stylesheet" href="src.css">
<script src="https://kit.fontawesome.com/ecdaf24e6f.js" crossorigin="anonymous"></script>
<style>
body {
    font-family: Arial, sans-serif;
    background: #202020;
    color: #fff;
    margin: 0;
    padding: 0;
}

.containere {
    max-width: 900px;
    margin: 50px auto;
    padding: 0 20px;
}

.promo-card {
    display: flex;
    flex-wrap: wrap;
    background: #111;
    border-radius: 10px;
    padding: 30px;
    gap: 20px;
    border: 1px solid #333;
    box-shadow: 0 0 15px rgba(255, 50, 50, 0.3);
}

.promo-left {
    flex: 1;
    min-width: 250px;
}

.promo-right {
    flex: 2;
}

.promo-right h1 {
    font-size: 32px;
    margin-bottom: 15px;
    color: crimson;
}

.promo-right p {
    font-size: 16px;
    line-height: 1.6;
}

button {
    background-color: #202020ff;
    border: 2px solid crimson;
    color: white;
    padding: 12px 25px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 16px;
    margin-top: 20px;
    transition: 0.3s;
}

button:hover {
    background-color: darkred;
}

@media(max-width:800px){
    .promo-card {
        flex-direction: column;
        align-items: center;
        text-align: center;
    }

    .promo-right {
        width: 100%;
    }
}
</style>
</head>
<body>

<div class="containere">
    <div class="promo-card">
        <div class="promo-left">
            <div class="promo-left">
    <img src="<?php echo !empty($promo['promo_img']) ? htmlspecialchars($promo['promo_img']) : 'img/promo_default.png'; ?>" 
         alt="<?php echo htmlspecialchars($promo['promo_name']); ?>" 
         width="280" height="280" 
         style="border-radius:10px; border:2px solid #444; object-fit:cover;">
</div>

        </div>

        <div class="promo-right">
            <h1><?php echo htmlspecialchars($promo['promo_name']); ?></h1>
            <p><strong>รหัสโปรโมชั่น:</strong> <?php echo htmlspecialchars($promo['promo_id']); ?></p>
            
            <hr style="border:1px solid #333;">
            <h1><strong>ราคา : </strong> ฿<?php echo number_format($promo['promo_price']); ?></h1>
            <p><strong>รายละเอียดโปรโมชั่น:</strong><br><?php echo nl2br(htmlspecialchars($promo['promo_description'])); ?></p>

            <?php if (!empty($promo['promo_details'])): ?>
                <p><strong>เงื่อนไขเพิ่มเติม:</strong><br><?php echo nl2br(htmlspecialchars($promo['promo_details'])); ?></p>
            <?php endif; ?>

            <p><strong>ประเภทส่วนลด:</strong>
                <?php echo ($promo['discount_type'] === 'percent') ? 'เปอร์เซ็นต์ (%)' : 'จำนวนเงิน (บาท)'; ?>
            </p>

            <p><strong>มูลค่าส่วนลด:</strong>
                <?php echo ($promo['discount_type'] === 'percent')
                    ? $promo['discount_value'] . '%'
                    : '฿' . number_format($promo['discount_value']); ?>
            </p>

            <p><strong>ระยะเวลาโปรโมชั่น:</strong>
                <?php echo date("d/m/Y", strtotime($promo['start_date'])); ?>
                - <?php echo date("d/m/Y", strtotime($promo['end_date'])); ?>
            </p>

            <p><strong>สถานะ:</strong> 
                <?php echo ($promo['status'] === 'active') ? "<span style='color:lime;'>เปิดใช้งาน</span>" : "<span style='color:gray;'>ปิด</span>"; ?>
            </p>
            
            <form method="post" action="add_promo_cart.php" class="add-cart">
                <input type="hidden" name="promo_id" value="<?php echo htmlspecialchars($promo['promo_id']); ?>">
                <input type="hidden" name="promo_name" value="<?php echo htmlspecialchars($promo['promo_name']); ?>">
                <input type="hidden" name="promo_price" value="<?php echo $promo['promo_price']; ?>">
                <input type="hidden" name="promo_img" value="<?php echo htmlspecialchars($promo['promo_img']); ?>">
                <br>
                <label>จำนวน : </label>
                <input type="number" name="quantity" value="1" min="1" style="width:60px; padding:5px; text-align:center;margin-right: 20px">
                <button type="submit" style="background-color:#202020ff;border: 2px solid crimson; color: #fff;">เพิ่มลงตะกร้า</button>
            </form>
            <a href="index.php"><button>กลับหน้าหลัก</button></a>
        </div>
    </div>
</div>

</body>
</html>
