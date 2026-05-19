<?php
session_start();
require 'db_conn.php'; 

if (!isset($_SESSION['uid'])) {
    header("Location: login.php"); 
    exit;
}

$user_id = $_SESSION['uid'];
$user_data = null;


$sql = "SELECT uid, u_name, u_email, u_role, u_phone, u_address, u_image, u_created_at 
        FROM users 
        WHERE uid = ? 
        LIMIT 1";

$stmt = $conn->prepare($sql);
$stmt->bind_param("s", $user_id); 
$stmt->execute();
$res = $stmt->get_result();

if ($res->num_rows === 1) {
    $user_data = $res->fetch_assoc();
} else {
    session_destroy();
    header("Location: login.php?error=data_not_found");
    exit;
}


$u_name = htmlspecialchars($user_data['u_name'] ?? 'N/A');
$u_email = htmlspecialchars($user_data['u_email'] ?? 'N/A');
$u_role = htmlspecialchars($user_data['u_role'] ?? 'N/A');
$u_phone = htmlspecialchars($user_data['u_phone'] ?? 'ไม่ได้ระบุ'); 
$u_address = htmlspecialchars($user_data['u_address'] ?? 'ไม่ได้ระบุ'); 
$u_image_file = htmlspecialchars($user_data['u_image'] ?? '');           
$u_created_at = date('d/m/Y H:i', strtotime($user_data['u_created_at'] ?? ''));


$default_image = 'path/to/default_profile.png'; 
$profile_image_path = empty($u_image_file) ? $default_image : 'uploads/profile/' . $u_image_file;

$status_message = '';
if (isset($_GET['status']) && $_GET['status'] === 'updated') {
    $status_message = '<div class="message-success">✅ ข้อมูลส่วนตัวถูกบันทึกเรียบร้อยแล้ว</div>';
}

?>
<!doctype html>
<html lang="th">

<head>
    <meta charset="utf-8">
    <title>ข้อมูลโปรไฟล์ของ <?php echo $u_name; ?></title>
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

        .profile-container {
            width: 95%; 
            max-width: 1200px; 
            background-color: #000; 
            border-radius: 15px;
            box-shadow: none; 
            padding: 40px; 
            box-shadow: 0 5px 20px rgba(220, 20, 60, 0.4);
            border: 2px solid crimson;
        }

        .message-success {
            opacity: 1; 
            padding: 15px;
            background-color: #28a745; 
            color: white;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: 600;
        }

        .profile-content {
            display: flex;
            gap: 40px;
            align-items: flex-start;
        }

        .left-column {
            flex: 0 0 300px; 
            padding: 20px;
            background-color: #252525; 
            border-radius: 10px;
            text-align: center;
        }
        
        .profile-picture {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background-color: #ffffff; 
            display: inline-flex;
            justify-content: center;
            align-items: center;
            font-size: 50px;
            font-weight: 700;
            color: #DC3545; 
            margin-bottom: 15px;
            overflow: hidden;
        }

        .profile-picture img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        h2.username {
            font-size: 24px;
            margin: 0 0 5px 0;
            color: #ffffff; 
        }

        p.role {
            color: #aaa; 
            font-size: 16px;
            margin-top: 0;
            text-transform: capitalize;
        }

        .right-column {
            flex-grow: 1; 
        }
        
        h3 {
            
            color: #DC3545; 
           

            margin-top: 0;
            margin-bottom: 20px;
        }

        .detail-block {
            display: flex; 
            justify-content: space-between;
            margin-bottom: 15px;
            padding: 10px 0;
            border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
        }
        
        .detail-block:last-of-type {
            border-bottom: none;
        }

        .detail-block strong {
            font-size: 16px;
            color: #ccc; 
            flex: 0 0 150px; 
        }

        .detail-block span {
            font-size: 16px;
            font-weight: 500;
            color: #ffffff; 
            flex-grow: 1;
            text-align: right;
        }
        
        .detail-address strong {
            text-align: locale_filter_matches !important;
        }
        .detail-address span {
            text-align: right !important;
            white-space: normal;
        }
        
        .action-links {
            margin-top: 40px; 
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1); 
            display: flex;
            gap: 15px;
            justify-content: flex-end; 
        }

        .action-links a {
            flex-grow: 0; 
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 6px;
            text-align: center;
            font-weight: 600;
            transition: background-color 0.3s;
            white-space: nowrap; 
        }

        .action-links .back-link {
            background-color: #202020ff; 
            color: #fff;
            border : 2px solid crimson;
        }

        .action-links .edit-link {
            background-color: #00a323ff; 
            border: 2px solid #aaa;
            color: white;
        }

        .action-links .edit-link:hover {
            background-color: #33ffaaff; 
        }

        .action-links .logout-link {
            background-color: crimson;
            border: 2px solid #aaa;
            color: white;
        }

        .action-links .logout-link:hover {
            background-color: #C82333;
        }

        hr {
            background-color: #dadadaff;
        }
        
        @media (max-width: 768px) {
            .profile-container {
                width: 100%;
                padding: 20px;
                border-radius: 0; 
                min-height: 100vh; 
            }
            .profile-content {
                flex-direction: column; 
                gap: 20px;
            }
            .left-column {
                flex: 1 1 auto;
                width: 100%;
                padding: 20px 0;
                background-color: transparent; 
            }
            .action-links {
                flex-direction: column;
                justify-content: center;
                background-color: #202020ff;
                border: 2px solid crimson;
                gap: 10px;
            }
            .action-links a {
                flex-grow: 1;
            }
            .detail-block {
                flex-direction: column;
                align-items: flex-start;
            }
            .detail-block span {
                text-align: left;
                margin-top: 5px;
            }
            .detail-block strong {
                flex: none;
                margin-bottom: 5px;
            }
        }
    </style>
</head>

<body>
    <div class="profile-container">
        
        <?php echo $status_message; ?> 

        <div class="profile-content">
            
            <div class="left-column">
                <div class="profile-picture">
                    <?php if (!empty($u_image_file) && file_exists('uploads/profile/' . $u_image_file)): ?>
                        <img src="<?php echo $profile_image_path; ?>" alt="Profile Picture">
                    <?php else: ?>
                        <img src="<?php echo $default_image; ?>" alt="Default Profile Picture">
                    <?php endif; ?>
                </div>
                <h2 class="username"><?php echo $u_name; ?></h2>
                <p class="role">สิทธิ์ผู้ใช้งาน: <?php echo ucfirst($u_role); ?></p>
            </div>

            <div class="right-column">
                <h3>ข้อมูลติดต่อ</h3>
                <hr>

                <div class="detail-block">
                    <strong>อีเมล (Email)</strong>
                    <span><?php echo $u_email; ?></span>
                </div>
                
                <div class="detail-block">
                    <strong>เบอร์โทรศัพท์ (Phone)</strong>
                    <span><?php echo $u_phone; ?></span>
                </div>
                
                <div class="detail-block detail-address">
                    <strong>ที่อยู่</strong>
                    <span><?php echo nl2br($u_address); ?></span>
                </div>

                <h3 style="margin-top: 30px;">ข้อมูลระบบ</h3>
                <hr>
                
                <div class="detail-block">
                    <strong>บัญชีผู้ใช้ (Username)</strong>
                    <span><?php echo $u_name; ?></span>
                </div>
                
                <div class="detail-block">
                    <strong>วันที่สมัครใช้งาน</strong>
                    <span><?php echo $u_created_at; ?></span>
                </div>
                
            </div>
        </div>
        
        <div class="action-links">
            <a href="index.php" class="back-link">กลับหน้าหลัก</a>
            <a href="edit_profile.php" class="edit-link">แก้ไขโปรไฟล์</a> 
            <a href="logout.php" class="logout-link">ออกจากระบบ</a>
        </div>
    </div>
    
    <script>
    const successMessage = document.querySelector('.message-success');

    if (successMessage) {

        setTimeout(() => {

            successMessage.style.transition = 'opacity 1s ease-out';
            successMessage.style.opacity = '0';

            setTimeout(() => {
                successMessage.remove();
            }, 1000); 
            
        }, 3000); 
    }
    </script>
</body>
</html>