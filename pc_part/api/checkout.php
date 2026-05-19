<?php
session_start();


$total = $_POST['total'];
$cart_items = [
    ['name' => 'คีย์บอร์ด Mechanical RGB', 'qty' => 1, 'price' => 990],
    ['name' => 'เมาส์ไร้สาย', 'qty' => 1, 'price' => 210]
];
$_SESSION['cart'] = $cart_items;
$_SESSION['total'] = $total;
?>

<!DOCTYPE html>
<html lang="th">

<head>
    <meta charset="UTF-8">
    <title>ชำระเงิน</title>
    <style>
        body {
            background: #202020;
            color: #fff;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }

        .container {
            background: #2b2b2b;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.6);
            width: 420px;
        }

        h2 {
            color: crimson;
            text-align: center;
            margin-bottom: 15px;
        }

        p {
            text-align: center;
            font-size: 18px;
        }

        label {
            display: block;
            margin: 10px 0;
            cursor: pointer;
        }

        input[type="radio"] {
            margin-right: 8px;
            accent-color: crimson;
        }

        .section {
            display: none;
            margin-top: 15px;
        }

        input,
        textarea {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 8px;
            margin-bottom: 10px;
            background: #3a3a3a;
            color: #fff;
        }

        button {
            background: crimson;
            color: #fff;
            border: none;
            padding: 12px;
            border-radius: 10px;
            cursor: pointer;
            width: 100%;
        }

        button:hover {
            background: #ff5050;
        }

        img.qr {
            width: 200px;
            margin: 15px auto;
            display: block;
            border-radius: 10px;
            background: #fff;
            padding: 5px;
        }

        label {
            text-align: center;
        }
    </style>
</head>

<body>

    <div class="container">
        <h2>💳 ชำระเงิน</h2>
        <p>ยอดรวมทั้งหมด: <b>฿<?php echo number_format($total); ?></b></p>

        <form action="status.php" method="post">

            <hr>
            <!-- โอนผ่านธนาคาร -->
             <label><input type="radio" name="payment_method" value="bank" required> โอนผ่านธนาคาร</label>
            <div id="bank" class="section">
                <h3>สแกน QR เพื่อชำระเงิน</h3>
                <img src="qr_tech.png" alt="QR T.A.K Tech" class="qr">
                <p>ชื่อบัญชี: <b>บริษัท T.A.K Tech</b></p>
            </div>

            <hr>
            <!-- บัตรเครดิต -->
             <label><input type="radio" name="payment_method" value="credit" required> บัตรเครดิต</label>
            <div id="credit" class="section">
                <h3>กรอกข้อมูลบัตรเครดิต</h3>
                <input type="text" name="card_name" placeholder="ชื่อบนบัตร" required>
                <input type="text" name="card_number" maxlength="16" placeholder="หมายเลขบัตรเครดิต" required>
                <input type="text" name="exp" maxlength="5" placeholder="MM/YY" required>
                <input type="text" name="cvv" maxlength="3" placeholder="CVV" required>
            </div>

            <hr>
            <!-- เก็บเงินปลายทาง -->
             <label><input type="radio" name="payment_method" value="cod" required> เก็บเงินปลายทาง</label>
            <div id="cod" class="section">
                <h3>ข้อมูลผู้รับสินค้า</h3>
                <input type="text" name="fullname" placeholder="ชื่อ-นามสกุล" required>
                <input type="text" name="phone" placeholder="เบอร์โทรศัพท์" required>
            </div>

            <hr>
            <!-- ที่อยู่ -->
            <div id="addressSection" class="section">
                <h3>ที่อยู่จัดส่ง</h3>
                <textarea name="address" rows="3" placeholder="บ้านเลขที่, ถนน, เขต/อำเภอ, จังหวัด, รหัสไปรษณีย์" required></textarea>
            </div>

            <input type="hidden" name="total" value="<?php echo $total; ?>">
            <button type="submit">ยืนยันการชำระเงิน</button>
        </form>
    </div>

    <script>
        const radios = document.querySelectorAll('input[name="payment_method"]');
        const sections = document.querySelectorAll('.section');
        radios.forEach(r => {
            r.addEventListener('change', () => {
                sections.forEach(s => s.style.display = 'none');
                document.getElementById(r.value).style.display = 'block';
                document.getElementById('addressSection').style.display = 'block';
            });
        });
    </script>

</body>

</html>