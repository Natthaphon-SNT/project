<?php
session_start();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="src.css">
    <link rel="icon" href="icon.jpg" type="image/gif" sizes="16x16">
    
    <title>T.A.K Tech</title>
    <style>
    .top-bar {
        width: 200px;
        position: absolute;        
         
        top: 0;                    
        right: 0px;                 
        padding: 0px 50px;
        font-family: sans-serif;
        display: absolute;
        justify-content: center;
        align-items: center;      
        z-index: 1000;             
        color: #ddd;
        background-color: #202020ff; 
    }

    head {
        background-color: #202020ff;
    }

    .right-buttons {
        display: inherit;            
        align-items: flex-end;
        gap: 20px;
    }

    .top-bar .btn {
        background-color: #ff4d4d;
        color: white;
        padding: 8px 50px;
        border-radius: 5px;
        text-decoration: none;
        font-size: 14px;
    }

    .top-bar .btn:hover {
        background-color: #ff3333;
    }

    .top-bar .welcome {
        color: #ffffffff;
        font-size: 14px;
    }

    body {
        background-color: #202020ff;
        margin: 0;
        padding-top: 10px;
    }

    </style>
</head>
<body>
    <div class="top-bar">
    <div class="right-buttons">

        <?php if (isset($_SESSION['u_name'])): ?>
            <span class="welcome">
                ยินดีต้อนรับ <strong><?php echo htmlspecialchars($_SESSION['u_name'], ENT_QUOTES); ?></strong> |
                <a href="logout.php" style="color: #aaa;">ออกจากระบบ</a>
            </span>
        <?php else: ?>
            <span class="welcome">
                <a href="login.php">เข้าสู่ระบบ</a> |
                <a href="register.php">สมัครสมาชิก</a>
            </span>
        <?php endif; ?>
    </div>
</div>
</body>
</html>
