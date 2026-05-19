<?php
header("Access-Control-Allow-Origin: *"); 
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With");
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

header("Content-Type: application/json; charset=UTF-8");

include '../db_conn.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $uid =  trim($_POST['uid'] ?? '');
    $u_name = trim($_POST['u_name'] ?? '');
    $u_email = trim($_POST['u_email'] ?? '');
    $u_phone = trim($_POST['u_phone'] ?? '');
    $dob = trim($_POST['dob'] ?? '');
    $u_password = trim($_POST['u_password'] ?? '');
    $confirm = trim($_POST['confirm'] ?? '');


    if ($u_name === '' || $u_email === '' || $u_password === '' || $confirm === '' || $u_phone === '' || $dob === '') {
        $error = "กรุณากรอกข้อมูลให้ครบถ้วน";
    } elseif ($u_password !== $confirm) {
        $error = "รหัสผ่านไม่ตรงกัน";
    } elseif (!filter_var($u_email, FILTER_VALIDATE_EMAIL)) {
        $error = "รูปแบบอีเมลไม่ถูกต้อง";
    } else {
        $check = $conn->prepare("SELECT uid FROM users WHERE u_email = ? LIMIT 1");
        $check->bind_param("s", $u_email);
        $check->execute();
        $check->store_result();
        if ($check->num_rows > 0) {
            $error = "อีเมลนี้ถูกใช้งานแล้ว";
            $check->close();
        } else {
            $check->close();
            $hashedPassword = password_hash(trim($u_password), PASSWORD_DEFAULT);
            $sql = "INSERT INTO users (uid, u_name, u_email, u_password, u_phone, dob) VALUES (?, ?, ?, ?, ?, ?)";
            $stmt = $conn->prepare($sql);
            if ($stmt) {
                $stmt->bind_param("ssssss", $uid, $u_name, $u_email, $hashedPassword, $u_phone, $dob);
                if ($stmt->execute()) {
                    $_SESSION['user'] = $u_name;
                    header("Location: index.php");
                    exit;
                } else {
                    $error = "ไม่สามารถสมัครได้: " . $stmt->error;
                }
                $stmt->close();
            } else {
                $error = "เกิดข้อผิดพลาดในการเตรียมคำสั่ง SQL: " . $conn->error;
            }
        }
    }
}
?>
<!doctype html>
<html lang="th">

<head>
    <meta charset="utf-8">
    <title>Register</title>

    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #333 0%, #111 100%);
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 400px;
            margin: 60px auto;
            padding: 40px;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            text-align: center;
        }

        h1 {
            margin-bottom: 40px;
            font-size: 28px;
            color: #333;
        }

        .menu {
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
        }

        p,
        label {
            display: block;
            margin-bottom: 10px;
        }


        input[type="text"],
        input[type="password"],
        input[type="date"] {
            width: 300px;
            height: 40px;
            padding: 8px 12px;
            border: 1px solid #ccc;
            border-radius: 6px;
            font-size: 16px;
            box-sizing: border-box;
            margin: 10px auto;
            align-items: flex;
            display: block;
            margin: 10px auto;

        }

        input[name="username"],
        input[name="password"],
        input[name="confirm"] {
            margin-top: 20px;
        }

        input[type="submit"] {

            color: #ffffffff;
            background-color: #3e722bff;
        }

        button {

            color: #ffffffff;
            background-color: red;
        }

        button:hover {
            background: #cc0000;
        }

        input[type="submit"],
        button {

            width: 120px;
            height: 40px;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            color: #fff;

        }

        
 .form-action {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-top: 20px;
    }

    </style>
</head>

<body>
    <div class="container">
        <h1>สมัครสมาชิก</h1>
        <?php if (isset($error))
            echo "<p style='color:red'>$error</p>"; ?>
        <form method="post">
            <p><label>User ID: </label> <input type="text" name="uid" placeholder="Ex. u007"></p>
            <p><label>Username: </label> <input type="text" name="u_name"></p>
            <p><label>Email: </label> <input type="text" name="u_email"></p>
            <p><label>Tel: </label> <input type="text" name="u_phone" placeholder="Ex. 0999999999"></p>
            <p><label>วัน เดือน ปี เกิด: </label> <input type="date" name="dob"></p>
            <p><label>Password: </label> <input type="password" name="u_password"></p>
            <p><label>Confirm Password: </label> <input type="password" name="confirm"></p>
            <div class="form-action">
                <input type="submit" value="Register">
                <a href="login.php"><button type="button">กลับไปหน้า Login</button></a>
        </form>
    </div>
    </div>
</body>

</html>