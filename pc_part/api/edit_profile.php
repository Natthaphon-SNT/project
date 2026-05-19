<?php
session_start();
require 'db_conn.php'; 

if (!isset($_SESSION['uid'])) {
    header("Location: login.php");
    exit;
}

$user_id = $_SESSION['uid'];
$error = '';
$user_data = [];
$upload_dir = 'uploads/profile/'; 
$default_image = 'path/to/default_profile.png'; 

if (!is_dir($upload_dir)) {
    mkdir($upload_dir, 0777, true);
}


$sql_fetch = "SELECT u_name, u_email, u_phone, u_address, u_image FROM users WHERE uid = ? LIMIT 1";
$stmt_fetch = $conn->prepare($sql_fetch);
$stmt_fetch->bind_param("s", $user_id); 
$stmt_fetch->execute();
$res_fetch = $stmt_fetch->get_result();

if ($res_fetch->num_rows === 1) {
    $user_data = $res_fetch->fetch_assoc();
} else {
    session_destroy();
    header("Location: login.php?error=data_not_found");
    exit;
}


if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $new_name = trim($_POST['u_name'] ?? ''); 
    $new_phone = trim($_POST['u_phone'] ?? '');
    $new_address = trim($_POST['u_address'] ?? '');
    $new_image_file = $user_data['u_image']; 
    $current_email = $user_data['u_email']; 


    if (empty($new_name) || empty($new_phone) || empty($new_address)) {
        $error = "กรุณากรอกข้อมูลให้ครบถ้วน";
    } else {
        $can_update = true;


        if (isset($_FILES['u_image']) && $_FILES['u_image']['error'] === UPLOAD_ERR_OK) {
            $file_tmp = $_FILES['u_image']['tmp_name'];
            $file_name = $_FILES['u_image']['name'];
            $file_ext = strtolower(pathinfo($file_name, PATHINFO_EXTENSION));
            $allowed_ext = ['jpg', 'jpeg', 'png', 'gif'];

            if (!in_array($file_ext, $allowed_ext)) {
                $error = "อนุญาตเฉพาะไฟล์รูปภาพ (JPG, JPEG, PNG, GIF) เท่านั้น";
                $can_update = false;
            } else {
                $new_file_name = $user_id . '_' . time() . '.' . $file_ext;
                $target_file = $upload_dir . $new_file_name;

                if (move_uploaded_file($file_tmp, $target_file)) {
       
                    if (!empty($user_data['u_image']) && file_exists($upload_dir . $user_data['u_image'])) {
                        unlink($upload_dir . $user_data['u_image']);
                    }
                    $new_image_file = $new_file_name;
                } else {
                    $error = "เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ";
                    $can_update = false;
                }
            }
        }

        if ($can_update) {

            $sql_update = "UPDATE users SET u_name = ?, u_phone = ?, u_address = ?, u_image = ? WHERE uid = ?";
            $stmt_update = $conn->prepare($sql_update);
            
            if ($stmt_update) {
                $stmt_update->bind_param("sssss", $new_name, $new_phone, $new_address, $new_image_file, $user_id);
                
                if ($stmt_update->execute()) {

                    header("Location: profile.php?status=updated");
                    exit; 
                } else {
                    $error = "เกิดข้อผิดพลาดในการอัปเดต: " . $conn->error;
                }
                $stmt_update->close();
            } else {
                 $error = "เกิดข้อผิดพลาดในการเตรียมคำสั่ง: " . $conn->error;
            }
        }
    }
    

    $user_data['u_name'] = $new_name;
    $user_data['u_phone'] = $new_phone;
    $user_data['u_address'] = $new_address;
}


$current_name = htmlspecialchars($user_data['u_name'] ?? '');
$current_email = htmlspecialchars($user_data['u_email'] ?? '');
$current_phone = htmlspecialchars($user_data['u_phone'] ?? '');
$current_address = htmlspecialchars($user_data['u_address'] ?? '');
$current_image_file = htmlspecialchars($user_data['u_image'] ?? '');

?>
<!doctype html>
<html lang="th">

<head>
    <meta charset="utf-8">
    <title>แก้ไขโปรไฟล์</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #202020ff 0%, #000000 100%); 
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: #ffffff;
        }

        .edit-form-container {
            width: 95%; 
            max-width: 900px; 
            background-color: #000; 
            padding: 40px;
            border-radius: 15px;
            box-shadow: none; 
            box-shadow: 0 5px 20px rgba(220, 20, 60, 0.4);
            border: 2px solid crimson;
        }

        h1 {
            color: #DC3545; 
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 10px;
        }
        
        .message-error {
            color: #DC3545; 
            background-color: rgba(220, 53, 69, 0.1);
            border: 1px solid #DC3545;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        
        .form-layout {
            display: flex;
            gap: 40px;
            align-items: flex-start;
        }

        .left-side {
            flex: 0 0 300px; 
            text-align: center;
            padding: 20px;
            background-color: #252525;
            border-radius: 10px;
        }

        .right-side {
            flex-grow: 1; 
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #ccc;
        }

        input[type="text"],
        input[type="email"],
        input[type="tel"],
        textarea {
            width: 100%;
            padding: 12px;
            margin-bottom: 20px;
            border: 1px solid #555;
            border-radius: 6px;
            background-color: #333;
            color: #fff;
            box-sizing: border-box;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        textarea {
            resize: vertical;
            min-height: 80px;
        }

        input[type="email"][disabled] {
            background-color: #444; 
            color: #ccc;
            cursor: not-allowed;
        }

        input[type="text"]:focus,
        input[type="tel"]:focus,
        textarea:focus {
            border-color: #DC3545; 
            outline: none;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .action-buttons {
            display: flex;
            gap: 15px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1); 
            justify-content: flex-end;
        }

        button {
            flex-grow: 0;
            padding: 12px 20px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.3s;
            text-align: center;
            text-decoration: none;
            border: 2px solid #aaa;
            white-space: nowrap;
        }

        .cancel-link {
            flex-grow: 0;
            padding: 12px 20px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.3s;
            text-align: center;
            text-decoration: none;
            border: 2px solid crimson;
            white-space: nowrap;
            background-color: #202020ff;
        }

        button[type="submit"] {
            background-color: #009933; 
            color: white;
        }

        button[type="submit"]:hover {
            background-color: #006633; 
        }

        .cancel-link {
            background-color: #202020ff;
            color: white;
            line-height: 1.5; 
        }
        
        .cancel-link:hover {
            background-color: #C82333;
        }

        .image-preview {
            margin-bottom: 20px;
            
        }
        .current-image {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            object-fit: cover;
            margin-bottom: 10px;
        }
        .file-input {
            padding: 10px 0;
        }
        
        @media (max-width: 768px) {
            .edit-form-container {
                width: 100%;
                padding: 20px;
                border-radius: 0;
            }
            .form-layout {
                flex-direction: column;
                gap: 20px;
            }
            .left-side {
                flex: 1 1 auto;
                width: 100%;
            }
            .action-buttons {
                flex-direction: column;
                justify-content: center;
                gap: 10px;
            }
            button, .cancel-link {
                flex-grow: 1;
                
            }
        }
    </style>
</head>

<body>
    <div class="edit-form-container">
        <h1>แก้ไขข้อมูลส่วนตัว</h1>
        
        <?php if ($error): ?>
            <p class="message-error"><?php echo $error; ?></p>
        <?php endif; ?>

        <form method="post" enctype="multipart/form-data">
            
            <div class="form-layout">
                <div class="left-side">
                    <div class="image-preview">
                        <label>รูปโปรไฟล์</label><br>
                        <?php $current_image_path = (!empty($current_image_file) && file_exists($upload_dir . $current_image_file)) ? $upload_dir . $current_image_file : $default_image; ?>
                        <img src="<?php echo $current_image_path; ?>" class="current-image" alt="Current Profile Picture">
                        
                        <div class="file-input">
                            <input type="file" id="u_image" name="u_image" accept="image/*">
                            <small style="color: #aaa;">อัปโหลดเพื่อเปลี่ยนรูป</small>
                        </div>
                    </div>
                </div>

                <div class="right-side">
                    <div class="form-group">
                        <label for="u_name">ชื่อผู้ใช้งาน</label>
                        <input type="text" id="u_name" name="u_name" value="<?php echo $current_name; ?>" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="u_email">อีเมล (ไม่สามารถแก้ไขได้)</label>
                        <input type="email" id="u_email" value="<?php echo $current_email; ?>" disabled>
                    </div>

                    <div class="form-group">
                        <label for="u_phone">เบอร์โทรศัพท์</label>
                        <input type="tel" id="u_phone" name="u_phone" value="<?php echo $current_phone; ?>" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="u_address">ที่อยู่</label>
                        <textarea id="u_address" name="u_address"><?php echo $current_address; ?></textarea>
                    </div>
                </div>
            </div>
            
            <div class="action-buttons">
                <a href="profile.php" class="cancel-link">ยกเลิก</a> 
                <button type="submit">บันทึกการแก้ไข</button>
            </div>
        </form>
    </div>
</body>

</html>