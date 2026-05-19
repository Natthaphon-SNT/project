-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Mar 23, 2026 at 07:02 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `pc_part`
--

-- --------------------------------------------------------

--
-- Table structure for table `activity_logs`
--

CREATE TABLE `activity_logs` (
  `log_id` varchar(8) NOT NULL,
  `uid` varchar(8) NOT NULL,
  `l_action` varchar(100) NOT NULL,
  `l_description` text NOT NULL,
  `l_created_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `cart`
--

CREATE TABLE `cart` (
  `cart_id` varchar(8) NOT NULL,
  `uid` varchar(8) NOT NULL,
  `created_at` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `cart_item`
--

CREATE TABLE `cart_item` (
  `cart_item_id` varchar(8) NOT NULL,
  `cart_id` varchar(8) NOT NULL,
  `product_id` varchar(8) NOT NULL,
  `c_quantitty` decimal(10,0) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `categories`
--

CREATE TABLE `categories` (
  `cid` varchar(8) NOT NULL,
  `c_name` varchar(255) NOT NULL,
  `c_description` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `orders`
--

CREATE TABLE `orders` (
  `order_id` int(15) NOT NULL,
  `uid` varchar(8) NOT NULL,
  `order_date` date NOT NULL,
  `payment_method` varchar(50) NOT NULL,
  `total_amount` decimal(7,2) NOT NULL,
  `total_price` decimal(20,2) NOT NULL,
  `o_status` enum('pending','paid','shipped','completed','cancelled') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `orders`
--

INSERT INTO `orders` (`order_id`, `uid`, `order_date`, `payment_method`, `total_amount`, `total_price`, `o_status`) VALUES
(1, '', '2025-10-10', 'โอนผ่านธนาคาร', 1.00, 5790.00, 'pending'),
(2, '', '2025-10-10', 'เก็บเงินปลายทาง', 1.00, 9490.00, 'pending'),
(3, '', '2025-10-10', 'เก็บเงินปลายทาง', 1.00, 4290.00, 'pending'),
(4, '0', '2025-10-10', 'เก็บเงินปลายทาง', 1.00, 3690.00, 'pending'),
(5, '', '2025-10-10', 'เก็บเงินปลายทาง', 1.00, 3690.00, 'pending'),
(6, '', '2025-10-10', 'เก็บเงินปลายทาง', 1.00, 2500.00, 'pending'),
(7, '0', '2025-10-10', 'บัตรเครดิต', 1.00, 2500.00, 'pending'),
(8, '', '2025-10-10', 'เก็บเงินปลายทาง', 1.00, 2500.00, 'pending'),
(9, 'u002', '2025-10-10', 'เก็บเงินปลายทาง', 1.00, 3200.00, 'pending'),
(10, 'u001', '2025-10-10', 'โอนผ่านธนาคาร', 1.00, 9490.00, 'pending'),
(11, 'u001', '2025-10-10', 'โอนผ่านธนาคาร', 1.00, 3200.00, 'pending'),
(13, 'u001', '2025-10-17', 'โอนผ่านธนาคาร', 1.00, 3200.00, 'pending'),
(14, 'u009', '2025-10-20', 'เก็บเงินปลายทาง', 1.00, 3690.00, 'pending'),
(18, 'u025', '2025-10-22', 'โอนผ่านธนาคาร', 100.00, 320000.00, 'pending'),
(19, 'u025', '2025-10-22', 'โอนผ่านธนาคาร', 1.00, 16190.00, 'pending'),
(20, 'u025', '2025-10-22', 'โอนผ่านธนาคาร', 2.00, 16190.00, 'pending'),
(21, 'u025', '2025-10-22', 'โอนผ่านธนาคาร', 2.00, 16190.00, 'pending'),
(22, 'u025', '2025-10-22', 'โอนผ่านธนาคาร', 2.00, 16190.00, 'pending'),
(23, 'u002', '2025-10-22', 'โอนผ่านธนาคาร', 1.00, 16690.00, 'pending'),
(24, 'u002', '2025-10-22', 'บัตรเครดิต', 10.00, 151900.00, 'pending'),
(25, 'u002', '2025-11-01', 'โอนผ่านธนาคาร', 1.00, 5000.00, 'pending'),
(26, 'u123', '2025-11-01', 'บัตรเครดิต', 2.00, 8200.00, 'pending'),
(27, 'u002', '2025-11-02', 'โอนผ่านธนาคาร', 1.00, 5000.00, ''),
(28, 'u002', '2025-11-02', 'บัตรเครดิต', 1.00, 5000.00, 'paid'),
(29, 'u002', '2025-11-02', 'โอนผ่านธนาคาร', 1.00, 16690.00, 'paid');

-- --------------------------------------------------------

--
-- Table structure for table `order_items`
--

CREATE TABLE `order_items` (
  `order_item_id` int(255) NOT NULL,
  `order_id` varchar(8) NOT NULL,
  `product_id` varchar(8) NOT NULL,
  `oi_quantity` decimal(7,0) NOT NULL,
  `oi_price` decimal(7,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `order_items`
--

INSERT INTO `order_items` (`order_item_id`, `order_id`, `product_id`, `oi_quantity`, `oi_price`) VALUES
(1, '14', 'asd13', 1, 3200.00),
(2, '15', 'asd13', 1, 3200.00),
(3, '15', 'cp01', 1, 2500.00),
(4, '16', 'asd13', 1, 3200.00),
(5, '16', 'mb02', 1, 1490.00),
(6, '17', 'asd13', 1, 3200.00),
(7, '19', 'asd13', 1, 3200.00),
(8, '19', 'gpu03', 1, 5790.00),
(9, '1', 'gpu03', 1, 5790.00),
(10, '2', 'gpu08', 1, 9490.00),
(11, '3', 'cp08', 1, 4290.00),
(12, '4', 'cp05', 1, 3690.00),
(13, '5', 'cp04', 1, 3690.00),
(14, '6', 'cp01', 1, 2500.00),
(15, '7', 'cp01', 1, 2500.00),
(16, '8', 'cp01', 1, 2500.00),
(17, '9', 'asd13', 1, 3200.00),
(18, '10', 'gpu08', 1, 9490.00),
(19, '11', 'asd13', 1, 3200.00),
(20, '13', 'asd13', 1, 3200.00),
(21, '14', 'cp05', 1, 3690.00),
(22, '18', 'asd13', 100, 3200.00),
(23, '23', 'CS006', 1, 16690.00),
(24, '24', 'CS004', 10, 15190.00),
(25, '25', 'CS10', 1, 5000.00),
(26, '26', 'asd13', 1, 3200.00),
(27, '26', 'a101', 1, 5000.00),
(28, '27', 'CS10', 1, 5000.00),
(29, '28', 'CS10', 1, 5000.00),
(30, '29', 'CS006', 1, 16690.00);

-- --------------------------------------------------------

--
-- Table structure for table `payments`
--

CREATE TABLE `payments` (
  `payment_id` varchar(8) NOT NULL,
  `order_id` varchar(8) NOT NULL,
  `payment_date` date NOT NULL,
  `pa_amount` decimal(7,2) NOT NULL,
  `pa_method` enum('tranfer','credit_card','cod') NOT NULL,
  `pa_status` enum('pending','confirmed','failed') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `products`
--

CREATE TABLE `products` (
  `product_id` varchar(13) NOT NULL,
  `p_name` varchar(255) NOT NULL,
  `p_description` text NOT NULL,
  `p_price` decimal(10,2) NOT NULL,
  `price_advice` int(11) DEFAULT 0,
  `price_jib` int(11) DEFAULT 0,
  `price_ihavecpu` int(11) DEFAULT 0,
  `p_stock` int(20) NOT NULL,
  `cid` varchar(255) NOT NULL,
  `img_url` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `products`
--

INSERT INTO `products` (`product_id`, `p_name`, `p_description`, `p_price`, `price_advice`, `price_jib`, `price_ihavecpu`, `p_stock`, `cid`, `img_url`) VALUES
('a101', 'Apple', 'Just a apple.', 5000.00, 0, 0, 0, 0, 'a101', 'https://img.freepik.com/free-psd/close-up-delicious-apple_23-2151868338.jpg'),
('ac01', 'AIR COOLER (ซิงค์ลม) iHAVECPU UP1 SERIES WHITE ARGB (2Y)', 'Brands	iHAVECPU\r\nModel	iHAVECPU UP1\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-2066\r\nIntel® LGA-2011\r\nAMD AM4\r\nAMD AM2+\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	155 x 130 x 71 mm\r\nHeatpipes Quantity and Material	Ø6 mm *6 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	1 PCS\r\nFan Speed	600-1650 RPM+/- 10%\r\nFan Airflow	68 CFM\r\nFan Pressure	1.55 mm H20\r\nFan Noise Level	≤25 dB(A)\r\nFan Power Connector	4-Pin (PWM), 3-Pin (ARGB)\r\nLED Lighting	ARGB\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 890.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products74918_800.jpg'),
('ac02', 'AIR COOLER (ซิงค์ลม) ID-COOLING SE-214-XT-PLUS (2Y)', 'Brands	ID-COOLING\r\nModel	SE-214-XT PLUS\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-1151\r\nIntel® LGA-1150\r\nIntel® LGA-1155\r\nIntel® LGA-1156\r\nAMD AM4\r\nAMD AM5\r\nIntel® LGA-1851\r\nDimensions	98 x 124 x 150 mm\r\nHeatpipes Quantity and Material	4 x Ф6mm Heatpipe + Direct Touch + Aluminum Fin\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	700~1800 RPM±10%\r\nFan Airflow	76.16 CFM\r\nFan Pressure	2.15mmH2O\r\nFan MTTF	N/A\r\nFan Noise Level	35.2 dB(A)\r\nFan Power Connector	4-Pin (PWM)\r\nLED Lighting	N/A\r\nTDP	200W\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 890.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products45412_800.jpg'),
('ac03', 'AIR COOLER (ซิงค์ลม) iHAVECPU UP1 SERIES BLACK ARGB (2Y)', 'Brands	iHAVECPU\r\nModel	iHAVECPU UP1\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-2066\r\nIntel® LGA-2011\r\nAMD AM4\r\nAMD AM3+\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	155 x 130 x 71 mm\r\nHeatpipes Quantity and Material	Ø6 mm *6 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	1 PCS\r\nFan Speed	600-1650 RPM+/- 10%\r\nFan Airflow	68 CFM\r\nFan Pressure	1.55 mm H20\r\nFan Noise Level	≤25 dB(A)\r\nFan Power Connector	4-Pin (PWM), 3-Pin (ARGB)\r\nLED Lighting	ARGB\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 890.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products74914_800.jpg'),
('ac04', 'AIR COOLER (ซิงค์ลม) OCYPUS x iHAVECPU DELTA A40 DUAL FAN (BLACK) (2Y)', 'Brands	OCYPUS\r\nModel	DELTA A40 DUAL FAN\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nAMD AM4\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	95.5 x 125 x 156.7 mm\r\nHeatpipes Quantity and Material	Ø6 mm×4 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	500~2000 RPM±10%\r\nFan Airflow	73.0 CFM\r\nFan Pressure	4.3 mmH2O\r\nFan Noise Level	29 dB(A)\r\nFan Power Connector	4-Pin (PWM)\r\nTDP	220W\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 890.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products130720_800.jpg'),
('ac05', 'AIR COOLER (ซิงค์ลม) OCYPUS x iHAVECPU DELTA A40 DUAL FAN (WHITE) (2Y)', 'Brands	OCYPUS\r\nModel	DELTA A40 DUAL FAN\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nAMD AM4\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	95.5 x 125 x 156.7 mm\r\nHeatpipes Quantity and Material	Ø6 mm×4 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	500~2000 RPM±10%\r\nFan Airflow	73.0 CFM\r\nFan Pressure	4.3 mmH2O\r\nFan Noise Level	29 dB(A)\r\nFan Power Connector	4-Pin (PWM)\r\nTDP	220W\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 890.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products130710_800.jpg'),
('ac06', 'AIR COOLER (ซิงค์ลม) ID-COOLING FROZN A410 BLACK (2Y)', 'Brands	ID-COOLING\r\nModel	FROZN A410\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-1151\r\nIntel® LGA-1150\r\nIntel® LGA-1155\r\nIntel® LGA-1156\r\nAMD AM4\r\nAMD AM5\r\nIntel® LGA-1851\r\nDimensions	73 x 120 x 152 mm\r\nHeatpipes Quantity and Material	4 x Ф6mm Heatpipe + Direct Touch + Aluminum Fin\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	1 PCS\r\nFan Speed	500±200~2000 RPM±10%\r\nFan Airflow	78.25 CFM\r\nFan Pressure	2.68mmH2O\r\nFan MTTF	N/A\r\nFan Noise Level	29.85dB(A) Max.\r\nFan Power Connector	4-Pin (PWM)\r\nTDP	220W\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 990.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product42723_800.jpg'),
('ac07', 'AIR COOLER (ซิงค์ลม) OCYPUS x iHAVECPU DELTA A40 ARGB (BLACK) (2Y)', 'Brands	OCYPUS\r\nModel	DELTA A40 ARGB\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nAMD AM4\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	125 x 70.5 x 156.7 mm\r\nHeatpipes Quantity and Material	Ø6 mm×4 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	1 PCS\r\nFan Speed	500~2000 RPM±10%\r\nFan Airflow	73.0 CFM\r\nFan Pressure	4.3 mmH2O\r\nFan Noise Level	29 dB(A)\r\nFan Power Connector	4-Pin (PWM) 3-Pin (ARGB)\r\nLED Lighting	ARGB\r\nTDP	220W\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 990.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products124356_800.jpg'),
('ac08', 'AIR COOLER (ซิงค์ลม) OCYPUS x iHAVECPU DELTA A40 ARGB (WHITE) (2Y)', 'Brands	OCYPUS\r\nModel	DELTA A40 ARGB\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nAMD AM4\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	125 x 70.5 x 156.7 mm\r\nHeatpipes Quantity and Material	Ø6 mm×4 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	1 PCS\r\nFan Speed	500~2000 RPM±10%\r\nFan Airflow	73.0 CFM\r\nFan Pressure	4.3 mmH2O\r\nFan Noise Level	29 dB(A)\r\nFan Power Connector	4-Pin (PWM) 3-Pin (ARGB)\r\nLED Lighting	ARGB\r\nTDP	220W\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 990.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products124348_800.jpg'),
('ac09', 'AIR COOLER (ซิงค์ลม) DEEPCOOL AK400 BLACK (3Y)', 'Brands	DEEPCOOL\r\nModel	AK400\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-1151\r\nIntel® LGA-1150\r\nIntel® LGA-1155\r\nAMD AM4\r\nAMD AM5\r\nIntel® LGA-1851\r\nDimensions	127 x 97 x 155 mm\r\nHeatpipes Quantity and Material	Ø6 mm×4 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	1 PCS\r\nFan Speed	500~1850 RPM±10%\r\nFan Airflow	66.47 CFM\r\nFan Pressure	2.04 mmAq\r\nFan Noise Level	29 dB(A)\r\nFan Power Connector	4-Pin (PWM)\r\nTDP	220W\r\nCooler Type	Air Cooler\r\nWarranty	3 Years', 990.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product17518_800.jpg'),
('ac10', 'AIR COOLER (ซิงค์ลม) iHAVECPU RK500 DIGITAL TEMP BLACK (1Y)', 'Brands	iHAVECPU\r\nModel	RK500\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-1151\r\nIntel® LGA-1150\r\nIntel® LGA-1155\r\nIntel® LGA-1156\r\nAMD AM4\r\nAMD AM3+\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	120 x 97 x 159 mm\r\nHeatpipes Quantity and Material	Ø6 mm×5 pcs Aluminum Fin with a coating layer\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	800~2000 RPM±10%\r\nFan Airflow	60 CFM (Max)\r\nFan Pressure	2.4mm H2O\r\nFan Noise Level	32 dB(A)\r\nFan Power Connector	4-Pin (PWM), 3-Pin (ARGB)\r\nLED Lighting	ARGB\r\nCooler Type	Air Cooler\r\nWarranty	1 Year', 1190.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products83346_800.jpg'),
('ac11', 'AIR COOLER (ซิงค์ลม) iHAVECPU RK500 DIGITAL TEMP WHITE (1Y)', 'Brands	iHAVECPU\r\nModel	RK500\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-1151\r\nIntel® LGA-1150\r\nIntel® LGA-1155\r\nIntel® LGA-1156\r\nAMD AM4\r\nAMD AM3+\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	120 x 97 x 159 mm\r\nHeatpipes Quantity and Material	Ø6 mm×5 pcs Aluminum Fin with a coating layer\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	800~2000 RPM±10%\r\nFan Airflow	60 CFM (Max)\r\nFan Pressure	2.4mm H2O\r\nFan Noise Level	32 dB(A)\r\nFan Power Connector	4-Pin (PWM), 3-Pin (ARGB)\r\nLED Lighting	ARGB\r\nCooler Type	Air Cooler\r\nWarranty	1 Year', 1190.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products83352_800.jpg'),
('ac12', 'AIR COOLER (ซิงค์ลม) iHAVECPU UP2 SERIES BLACK ARGB (2Y)', 'Brands	iHAVECPU\r\nModel	iHAVECPU UP2\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-2066\r\nIntel® LGA-2011\r\nAMD AM4\r\nAMD AM3+\r\nAMD AM5\r\nIntel® LGA-115X\r\nIntel® LGA-1851\r\nDimensions	155 x 130 x 122 mm\r\nHeatpipes Quantity and Material	Ø6 mm *8 pcs\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	600-1650 RPM+/- 10%\r\nFan Airflow	68 CFM\r\nFan Pressure	1.55 mm H20\r\nFan Noise Level	≤25 dB(A)\r\nFan Power Connector	4-Pin (PWM), 3-Pin (ARGB)\r\nLED Lighting	ARGB\r\nCooler Type	Air Cooler\r\nWarranty	2 Years', 1290.00, 0, 0, 0, 999, 'c09', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products74922_800.jpg'),
('c01', 'CASE (เคส) GIGABYTE C102 GLASS ICE (WHITE)(mATX) (1Y)', 'Brand	GIGABYTE\r\nModel	C102\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	410mm\r\nCPU Cooler Support	165mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n2 x USB-A\r\n1 x Audio Out / Mic-in\r\nExpansion Slots	5 Slots\r\nDrive Bays Support	3.5\" x1, 2.5\"x2\r\nFan Installment	120mm x2 Fans\r\nFan Support	\r\nFront : 3 x 120mm or 2 x 140mm\r\nTop : 3 x 120mm or 2 x 140mm\r\nSide : 2 x 120mm\r\nRear : 1 x 120mm\r\nRadiator Support	\r\nFront : 360mm\r\nTop : 360mm\r\nSide : 240mm\r\nRear : 120mm\r\nColor	WHITE\r\nDimensions D x W x H	450 x 210 x 450 mm\r\nWeight	5.79 Kg\r\nWarranty	1 Year', 1290.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products57887_800.jpg'),
('c02', 'CASE (เคส) iHAVECPU IHC R03 (WHITE)(mATX) (1Y)', 'Brand	iHAVECPU\r\nModel	R03\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	330mm\r\nCPU Cooler Support	175mm\r\nPower Supply Support	ATX, SFX, SFX - L\r\nFront I/O	USB 3.0 Type-A (x1) , USB 1.1 Type-A (x1) , Speaker/Mic-in Combo (x1) , Power , Reset\r\nExpansion Slots	4 Slots\r\nDrive Bays Support	3.5\" x2 , 2.5\"x1\r\nFan Installment	120mm x3 ARGB Fans\r\nFan Support	\r\nFront : 3 x 120mm\r\nTop : 2 x 120mm or 2 x 140mm\r\nRear : 1 x 120mm\r\nRadiator Support	Top : 240,280mm\r\nColor	WHITE\r\nDimensions D x W x H	365 x 200 x 395 mm\r\nWarranty	1 Year', 1290.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products74523_800.jpg'),
('c03', 'CASE (เคส) iHAVECPU OM01 (WHITE)(mATX) (1Y)', 'Brand	iHAVECPU\r\nModel	OM01\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	315mm\r\nCPU Cooler Support	180mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n1 x USB 3.0 Type-A Port\r\n1 x USB-A 1.0\r\n1 x Audio In & Out\r\nExpansion Slots	4 Slots\r\nDrive Bays Support	3.5\" x1+1 , 2.5\" x1\r\nFan Installment	3FANS ARGB\r\nFan Support	\r\nTop : 2 x 120mm or 2 x 140mm\r\nRear : 1 x 120mm\r\nBottom : 2 x 120mm\r\nRadiator Support	\r\nTop : 240mm\r\nRear : 120mm\r\nColor	WHITE\r\nDimensions D x W x H	218 x 330 x 380 mm\r\nWeight	3.5 kg\r\nWarranty	1 Year', 1290.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products98819_800.jpg'),
('c04', 'CASE (เคส) iHAVECPU IHC R06 ARGB (WHITE)(mATX) (1Y)', 'Brand	iHAVECPU\r\nModel	IHC R06\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	329mm\r\nCPU Cooler Support	175mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n1 x USB 2.0 Type-A Port\r\n1 x USB 3.0 Type-A Port\r\n1 x HD Audio\r\nExpansion Slots	4 Slots\r\nDrive Bays Support	3.5\" x 2 , 2.5\" x 1\r\nFan Installment	120mm x3 ARGB Fans\r\nFan Support	\r\nFront : 3 x 120mm or 2 x 140mm\r\nTop : 2 x 120mm or 2 x 140mm\r\nRear : 1 x 120mm\r\nBottom : 2 x 120mm\r\nRadiator Support	\r\nTop : 240,280mm\r\nRear : 120mm\r\nColor	WHITE\r\nDimensions D x W x H	380 x 220 x 410 mm\r\nWarranty	1 Year', 1350.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products112886_800.jpg'),
('c05', 'CASE (เคส) SAMA GZS WHITE (ATX)', 'Brand	SAMA\r\nModel	SAMA GZS\r\nForm Factor	Mid-Tower\r\nMainboard Support	\r\nATX\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	330mm\r\nCPU Cooler Support	177mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n1 x USB-A 3.0\r\n2 x USB-A 2.0\r\n1 x Audio Out / Mic-in\r\n1 x Power Button\r\n1 x LED Button\r\nExpansion Slots	7 Slots\r\nDrive Bays Support	3.5\" x2 , 2.5\" x2\r\nFan Installment	120mm x4 RGB Fans\r\nFan Support	\r\nFront : 3 x 120mm\r\nTop : 2 x 120mm or 2 x 140mm\r\nRear : 1 x 120mm\r\nRadiator Support	\r\nFront : 120,240,280,360mm\r\nTop : 240mm\r\nRear : 120mm\r\nColor	WHITE\r\nDimensions D x W x H	383 x 215 x 465 mm\r\nWeight	5.7 kg\r\nWarranty	1 Year', 1390.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products65223_800.jpg'),
('c06', 'CASE (เคส) iHAVECPU IHC 301TG (BLACK)(ATX)', 'Brand	iHAVECPU\r\nModel	301TG\r\nForm Factor	Mid-Tower\r\nMainboard Support	\r\nATX\r\nMicro-ATX\r\nVGA Support	330mm\r\nCPU Cooler Support	175mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n2 x USB-A 1.1\r\n1 x USB-A 3.0\r\n1 x Microphone Jack\r\n1 x HD Audio\r\n1 x Reset Button\r\n1 x Power Button\r\nExpansion Slots	7 Slots\r\nDrive Bays Support	3.5\" x 1 , 2.5\" x 2\r\nFan Installment	120mm x4 RGB Fans\r\nFan Support	\r\nFront : 3 x 120mm or 2 x 140mm\r\nTop : 2 x 120mm or 2 x 140mm\r\nRear : 1 x 120mm\r\nRadiator Support	\r\nFront : 360mm\r\nTop : 240mm\r\nRear : 120mm\r\nColor	BLACK\r\nDimensions D x W x H	335 x 216 x 385 mm\r\nWarranty	1 Year', 1390.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products84786_800.jpg'),
('c07', 'CASE (เคส) iHAVECPU IHC 301TG (WHITE)(ATX)', 'Brand	iHAVECPU\r\nModel	301TG\r\nForm Factor	Mid-Tower\r\nMainboard Support	\r\nATX\r\nMicro-ATX\r\nVGA Support	330mm\r\nCPU Cooler Support	175mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n1 x USB-A 3.0\r\n2 x USB-A 1.1\r\n1 x HD Audio\r\n1 x Microphone Jack\r\nExpansion Slots	7 Slots\r\nDrive Bays Support	3.5\" x 1 , 2.5\" x 2\r\nFan Installment	120mm x4 ARGB Fans\r\nFan Support	\r\nFront : 3 x 120mm or 2 x 140mm\r\nTop : 2 x 120mm or 2 x 140mm\r\nRear : 1 x 120mm\r\nRadiator Support	\r\nFront : 360mm\r\nTop : 240mm\r\nRear : 120mm\r\nColor	WHITE\r\nDimensions D x W x H	335 x 216 x 385 mm\r\nWarranty	1 Year', 1490.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products84792_800.jpg'),
('c08', 'CASE (เคส) iHAVECPU IHC 401TG (WHITE)(ATX)', 'Brand	iHAVECPU\r\nModel	401TG\r\nForm Factor	Mid-Tower\r\nMainboard Support	\r\nATX\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	305mm\r\nCPU Cooler Support	175mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n1 x USB-A 3.0\r\n2 x USB-A 1.1\r\n1 x Audio Out\r\n1 x Microphone Jack\r\nExpansion Slots	7 Slots\r\nDrive Bays Support	3.5\" x 1 , 2.5\" x 2\r\nFan Installment	120mm x4 ARGB Fans\r\nFan Support	\r\nFront : 3 x 120mm or 2 x 140mm\r\nTop : 2 x 120mm or 2 x 140mm\r\nRear : 1 x 120mm\r\nRadiator Support	\r\nFront : 360mm\r\nTop : 240mm\r\nRear : 120mm\r\nColor	WHITE\r\nDimensions D x W x H	335 x 216 x 445 mm\r\nWarranty	1 Year', 1490.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products84804_800.jpg'),
('c09', 'CASE (เคส) iHAVECPU G390 V2 (BLACK)(mATX) (1Y)', 'Brand	iHAVECPU\r\nModel	G390\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	380mm\r\nCPU Cooler Support	165mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n1 x USB 3.0 Type-A Port\r\n1 x USB-A 1.0\r\n1 x Audio In & Out\r\nExpansion Slots	5 Slots\r\nDrive Bays Support	3.5\" x1 , 2.5\"x2\r\nFan Installment	120mm x3 ARGB Fans\r\nFan Support	\r\nTop : 3 x 120mm\r\nSide : 2 x 120mm\r\nRear : 1 x 120mm\r\nBottom : 3 x 120mm\r\nRadiator Support	\r\nSide : 240mm\r\nRear : 120mm\r\nColor	BLACK\r\nDimensions D x W x H	395 x 228 x 415 mm\r\nWeight	4.1 kg\r\nWarranty	1 Year', 1490.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products98330_800.jpg'),
('c10', 'CASE (เคส) iHAVECPU G390 V2 (WHITE)(mATX) (1Y)', 'Brand	iHAVECPU\r\nModel	G390\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	380mm\r\nCPU Cooler Support	165mm\r\nPower Supply Support	ATX PSU\r\nFront I/O	\r\n1 x USB 3.0 Type-A Port\r\n1 x USB-A 1.0\r\n1 x Audio In & Out\r\nExpansion Slots	5 Slots\r\nDrive Bays Support	3.5\" x1 , 2.5\"x2\r\nFan Installment	120mm x3 ARGB Fans\r\nFan Support	\r\nTop : 3 x 120mm\r\nSide : 2 x 120mm\r\nRear : 1 x 120mm\r\nBottom : 3 x 120mm\r\nRadiator Support	\r\nSide : 240mm\r\nRear : 120mm\r\nColor	WHITE\r\nDimensions D x W x H	395 x 228 x 415 mm\r\nWeight	4.1 kg\r\nWarranty	1 Year', 1490.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products98333_800.jpg'),
('c11', 'CASE (เคส) iHAVECPU CRYSTAL Z9 MINI (BLACK)(mATX) (1Y)', 'Brand	iHAVECPU\r\nModel	CRYSTAL Z9 MINI\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	330mm\r\nCPU Cooler Support	160mm\r\nPower Supply Support	ATX, SFX, SFX - L\r\nFront I/O	\r\n1 x USB-A\r\n2 x USB-A\r\n1 x Audio Out\r\n1 x Microphone Jack\r\nExpansion Slots	5 Slots\r\nDrive Bays Support	3.5\" x2 , 2.5\" x1\r\nFan Installment	120mm x3 ARGB Fans\r\nFan Support	\r\nSide : 2 x 120mm\r\nRear : 1 x 120mm\r\nBottom : 2 x 120mm\r\nRadiator Support	Side : 240mm\r\nColor	BLACK\r\nDimensions D x W x H	340 x 270 x 379 mm\r\nWarranty	1 Year', 1490.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products69566_800.jpg'),
('c12', 'CASE (เคส) iHAVECPU IHC 102 WOOD (BLACK)(mATX) (1Y)', 'Brand	iHAVECPU\r\nModel	IHC 102\r\nForm Factor	Mini-Tower\r\nMainboard Support	\r\nMini-ITX\r\nMicro-ATX\r\nVGA Support	305mm\r\nCPU Cooler Support	175mm\r\nPower Supply Support	ATX\r\nFront I/O	\r\n1 x USB-A 3.0\r\n2 x USB-A\r\n1 x Audio In & Out\r\nExpansion Slots	4 Slots\r\nDrive Bays Support	3.5\" x 1,2.5\" x 1\r\nFan Installment	120mm x3 ARGB Fans\r\nFan Support	\r\nFront : 2 x 120mm or 2 x 140mm\r\nTop : 2 x 120mm\r\nRear : 1 x 120mm\r\nRadiator Support	\r\nFront : 240mm\r\nTop : 240mm\r\nRear : 120mm\r\nColor	BLACK\r\nDimensions D x W x H	358 x 218 x 403 mm\r\nWarranty	1 Year', 1490.00, 0, 0, 0, 999, 'c07', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products83412_800.jpg'),
('cp01', 'CPU (ซีพียู) AMD AM4 RYZEN 5 5500 3.6GHz 6C 12T', 'Brand	AMD\r\nSeries	5000 Series\r\nProcessor Number	Ryzen 5 5500\r\nSocket Type	AM4\r\nCores/Threads	6 Cores / 12 Threads\r\nBase Frequency	3.6 GHz\r\nMax Turbo Frequency	4.2 GHz\r\nL2 Cache	3 MB\r\nL3 Cache	16 MB\r\nGraphics Models	Discrete Graphics Card Required\r\n64Bit Support	N/A\r\nCPU Cooler	Yes\r\nDefault TDP	65W\r\nWarranty	3 Years', 2500.00, 0, 0, 0, 1000, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product735_800.jpg'),
('cp02', 'CPU (ซีพียู) AMD AM4 RYZEN 5 5600 3.5GHz 6C 12T', 'Brand	AMD\r\nSeries	5000 Series\r\nProcessor Number	Ryzen 5 5600\r\nSocket Type	AM4\r\nCores/Threads	6 Cores / 12 Threads\r\nBase Frequency	3.5 GHz\r\nMax Turbo Frequency	4.4 GHz\r\nL2 Cache	3 MB\r\nL3 Cache	32 MB\r\nGraphics Models	Discrete Graphics Card Required\r\n64Bit Support	N/A\r\nCPU Cooler	Yes\r\nDefault TDP	65W\r\nWarranty	3 Years', 2990.00, 0, 0, 0, 1500, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product736_800.jpg'),
('cp03', 'CPU (ซีพียู) AMD RYZEN 5 PRO 4650G [AM4] (MPK)', 'Brand	AMD\r\nSeries	PRO 4000 Series\r\nProcessor Number	Ryzen 5 PRO 4650G\r\nSocket Type	AM4\r\nCores/Threads	6 Cores / 12 Threads\r\nBase Frequency	3.7 GHz\r\nMax Turbo Frequency	4.2 GHz\r\nL2 Cache	3 MB\r\nL3 Cache	8 MB\r\nGraphics Models	AMD Radeon™ Graphics\r\n64Bit Support	Yes\r\nCPU Cooler	No\r\nDefault TDP	65W\r\nWarranty	3 Years', 3290.00, 0, 0, 0, 1000, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product43302_800.jpg'),
('cp04', 'CPU (ซีพียู) INTEL 1700 CORE I5-12400F 2.5GHz 6C 12T', 'Brand	INTEL\r\nSeries	12th Gen Intel® Core™ i5 Processor\r\nProcessor Number	CORE i5 -12400F\r\nSocket Type	LGA 1700\r\nCores/Threads	6 (6P) Cores / 12 Threads\r\nBase Frequency	2.5 GHz\r\nMax Turbo Frequency	4.4 GHz\r\nL2 Cache	7.5 MB\r\nL3 Cache	18 MB\r\nGraphics Models	Discrete Graphics Card Required\r\n64Bit Support	N/A\r\nCPU Cooler	Yes\r\nDefault TDP	65W\r\nMaximum Turbo Power	117W\r\nWarranty	3 Years', 3690.00, 0, 0, 0, 9999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products88916_800.jpg'),
('cp05', 'CPU (ซีพียู) AMD AM4 RYZEN 5 5500GT 3.6GHz 6C 12T', 'Brand	AMD\r\nSeries	5000 Series\r\nProcessor Number	Ryzen 5 5500GT\r\nSocket Type	AM4\r\nCores/Threads	6 Cores / 12 Threads\r\nBase Frequency	3.6 GHz\r\nMax Turbo Frequency	4.4 GHz\r\nL2 Cache	3 MB\r\nL3 Cache	16 MB\r\nGraphics Models	AMD Radeon™ Graphics\r\n64Bit Support	N/A\r\nCPU Cooler	Yes\r\nMaximum Turbo Power	65 Watt\r\nWarranty	3 Years', 3690.00, 0, 0, 0, 9999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products123932_800.jpg'),
('cp06', 'CPU (ซีพียู) AMD AM5 RYZEN 9 9950X3D 4.3GHz 16C 32T (3Y)', 'Brand	AMD\r\nSeries	9000 Series\r\nProcessor Number	Ryzen 9 9950X3D\r\nSocket Type	AM5\r\nCores/Threads	16 Core / 32 Threads\r\nBase Frequency	4.3 GHz\r\nMax Turbo Frequency	5.7 GHz\r\nL2 Cache	16 MB\r\nL3 Cache	64 MB\r\nGraphics Models	AMD Radeon Graphics\r\nCPU Cooler	No\r\nDefault TDP	170W\r\nWarranty	3 Years', 3690.00, 0, 0, 0, 999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products85479_800.jpg'),
('cp07', 'CPU (ซีพียู) AMD AM4 RYZEN 5 5500GT 3.6GHz 6C 12T (MPK) (3Y)', 'Brand	AMD\r\nSeries	5000 Series\r\nProcessor Number	Ryzen 5 5500GT\r\nSocket Type	AM4\r\nCores/Threads	6 Cores / 12 Threads\r\nBase Frequency	3.6 GHz\r\nMax Turbo Frequency	4.4 GHz\r\nL2 Cache	3 MB\r\nL3 Cache	16 MB\r\nGraphics Models	AMD Radeon Graphics\r\nCPU Cooler	Yes\r\nDefault TDP	65W\r\nWarranty	3 Years', 3690.00, 0, 0, 0, 999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products130112_800.jpg'),
('cp08', 'CPU (ซีพียู) AMD AM5 RYZEN 5 8400F 4.2GHz 6C 12T (MPK) (3Y)', 'Brand	AMD\r\nSeries	8000 Series\r\nProcessor Number	Ryzen 5 8400F\r\nSocket Type	AM5\r\nCores/Threads	6 Cores / 12 Threads\r\nBase Frequency	4.2 GHz\r\nMax Turbo Frequency	4.7 GHz\r\nL2 Cache	6 MB\r\nL3 Cache	16 MB\r\nGraphics Models	Discrete Graphics Card Required\r\nCPU Cooler	N/A\r\nDefault TDP	65W\r\nWarranty	3 Years', 4290.00, 0, 0, 0, 999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products120390_800.jpg'),
('cp09', 'CPU (ซีพียู) INTEL 1700 CORE I5-14400F 4.7GHz 10C 16T', 'Brand	INTEL\r\nSeries	14th Gen Intel® Core™ i5 Processor\r\nProcessor Number	CORE i5 -14400F\r\nSocket Type	LGA 1700\r\nCores/Threads	10 (6P+4E) Cores / 16 Threads\r\nBase Frequency	2.5 GHz\r\nMax Turbo Frequency	4.7 GHz\r\nL2 Cache	9.5 MB\r\nL3 Cache	20 MB\r\n64Bit Support	N/A\r\nCPU Cooler	Yes\r\nDefault TDP	65W\r\nMaximum Turbo Power	148W\r\nWarranty	3 Years', 4390.00, 0, 0, 0, 999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products123720_800.jpg'),
('cp10', 'CPU (ซีพียู) INTEL 1700 CORE I5-12400 2.5GHz 6C 12T (3Y)', 'Brand	INTEL\r\nSeries	12th Gen Intel® Core™ i5 Processor\r\nProcessor Number	CORE i5 -12400\r\nSocket Type	LGA 1700\r\nCores/Threads	6 (6P) Cores / 12 Threads\r\nBase Frequency	2.5 GHz\r\nMax Turbo Frequency	4.4 GHz\r\nL2 Cache	7.5 MB\r\nL3 Cache	18 MB\r\nGraphics Models	Intel® UHD Graphics 730\r\n64Bit Support	N/A\r\nCPU Cooler	Yes\r\nDefault TDP	65W\r\nMaximum Turbo Power	117W\r\nWarranty	3 Years', 4590.00, 0, 0, 0, 9999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products88925_800.jpg'),
('cp11', 'CPU (ซีพียู) AMD AM5 RYZEN 5 8500G 3.5GHz 6C 12T', 'Brand	AMD\r\nSeries	8000 Series\r\nProcessor Number	Ryzen 5 8500G\r\nSocket Type	AM5\r\nCores/Threads	6 Cores / 12 Threads\r\nBase Frequency	3.5 GHz\r\nMax Turbo Frequency	5.0 GHz\r\nL2 Cache	6 MB\r\nL3 Cache	16 MB\r\nGraphics Models	AMD Radeon™ 740M\r\n64Bit Support	N/A\r\nCPU Cooler	Yes\r\nDefault TDP	65W\r\nMaximum Turbo Power	65 Watt\r\nWarranty	3 Years', 5390.00, 0, 0, 0, 999, 'c01', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products123931_800.jpg'),
('gpu01', 'VGA(การ์ดจอ) POWERCOLOR FIGHTER RADEON RX 6500 XT - 4GB GDDR6 V3 (AXRX 6500XT 4GBD6-DHV3) (3Y)', 'Brands	POWER COLOR\r\nGPU Series	AMD Radeon™ RX 6000 Series\r\nGPU Model	Radeon™ RX 6500 XT\r\nMemory Size	4GB GDDR6\r\nBus Standards	PCI Express 4.0 x4\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	1024\r\nMemory Interface	64-bit\r\nBoost Clock	2815 MHz (OC mode)\r\nMemory Clock	18.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	1 x HDMI 2.1\r\nDisplay Port	1x DisplayPort™ 1.4\r\nPower Connector	1 x 6-pin\r\nPower Requirement	400 Watt\r\nDimension	192 x 127 x 42 mm\r\nWarranty	3 Years', 4790.00, 0, 0, 0, 9999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products103815_800.jpg'),
('gpu02', 'VGA(การ์ดจอ) MSI GEFORCE RTX 3050 VENTUS 2X 6G OC - 6GB GDDR6 (3Y)', 'Brand	MSI\r\nGPU Series	GeForce RTX™ 30 Series\r\nGPU Model	GeForce RTX™ 3050\r\nMemory Size	6 GB\r\nMemory Type	GDDR6\r\nCUDA® Cores	2304\r\nMemory Interface	96-bit\r\nBoost Clock	N/A\r\nBase Clock	1492 MHz\r\nInterface	PCI Express 4.0 x16\r\nMemory Clock	14.0 Gbps\r\nHDMI Port	2 x HDMI 2.1\r\nDisplay Port	1x DisplayPort™ 1.4a\r\nCooler Fan	2 Fans\r\nPower Requirement	300W\r\nPower Connectors	N/A\r\nWarranty	3 Years\r\nDimensions L x W x H	189 x 109 x 42 mm\r\nPower Range	300W', 5790.00, 0, 0, 0, 9999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product55002_800.jpg'),
('gpu03', 'VGA(การ์ดจอ) GIGABYTE GEFORCE RTX 3050 WINDFORCE OC V2 6G - 6GB GDDR6 (GV-N3050WF2OCV2-6GD) (3Y)', 'Brands	GIGABYTE\r\nGPU Series	NVIDIA GeForce RTX™ 30 Series\r\nGPU Model	GeForce RTX™ 3050\r\nMemory Size	6GB GDDR6\r\nBus Standards	PCI Express 4.0\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	2304\r\nMemory Interface	96-bit\r\nBoost Clock	1477 MHz (Reference Card : ) 1470 MHz\r\nBase Clock	1042 MHz\r\nMemory Clock	14.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	2 x HDMI 2.1\r\nDisplay Port	2x DisplayPort™ 1.4a\r\nPower Connector	N/A\r\nPower Requirement	300 Watt\r\nDimension	191 x 111 x 36 mm\r\nWarranty	3 Years', 5790.00, 0, 0, 0, 9999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products77610_800.jpg'),
('gpu04', 'VGA(การ์ดจอ) COLORFUL GEFORCE RTX 3050 6G V4-V - 6GB GDDR6 (3Y)', 'Brands	COLORFUL\r\nGPU Series	NVIDIA GeForce RTX™ 30 Series\r\nGPU Model	GeForce RTX™ 3050\r\nMemory Size	6GB GDDR6\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	2304\r\nMemory Interface	96-bit\r\nBoost Clock	1470 MHz\r\nBase Clock	1042 MHz\r\nMemory Clock	14.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	1 x HDMI\r\nDisplay Port	1 x DisplayPort\r\nDVI Port	1 x DVI-D\r\nPower Connector	N/A\r\nPower Requirement	450 Watt\r\nDimension	245 x 115 x 40.3 mm\r\nWarranty	3 Years', 5790.00, 0, 0, 0, 999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products125094_800.jpg'),
('gpu05', 'VGA(การ์ดจอ) INNO3D GEFORCE RTX 3050 TWIN X2 V2 - 6GB GDDR6 (N30502-06D6-1880VA60) (3Y)', 'Brands	INNO3D\r\nGPU Series	NVIDIA GeForce RTX™ 30 Series\r\nGPU Model	GeForce RTX™ 3050\r\nMemory Size	6GB GDDR6\r\nBus Standards	PCI Express 4.0 x16\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	2304\r\nMemory Interface	96-bit\r\nBoost Clock	1470 MHz\r\nBase Clock	1042 MHz\r\nMemory Clock	14.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	1 x HDMI 2.1\r\nDisplay Port	1x DisplayPort™ 1.4a\r\nDVI Port	1 x DVI-D\r\nPower Connector	N/A\r\nPower Requirement	450 Watt\r\nDimension	222 x 120 x 40 mm\r\nWarranty	3 Years', 5790.00, 0, 0, 0, 999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products125878_800.jpg'),
('gpu06', 'VGA(การ์ดจอ) XFX SPEEDSTER SWFT210 RADEON RX 7600 CORE - 8GB GDDR6 (RX-76PSWFTFY) (3Y)', 'Brands	XFX\r\nGPU Series	AMD Radeon™ RX 7000 Series\r\nGPU Model	Radeon™ RX 7600\r\nMemory Size	8GB GDDR6\r\nBus Standards	PCI Express 4.0\r\nCUDA® Cores	2048\r\nMemory Interface	128-bit\r\nBoost Clock	2655 MHz\r\nBase Clock	1875 MHz\r\nMemory Clock	18.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	1 x HDMI 2.1\r\nDisplay Port	3x DisplayPort™ 2.1\r\nPower Connector	1 x 8-pin\r\nPower Requirement	550 Watt\r\nDimension	241 x 131 x 41 mm\r\nWarranty	3 Years', 8290.00, 0, 0, 0, 999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products125105_800.jpg'),
('gpu07', 'VGA(การ์ดจอ) PALIT GEFORCE RTX 5050 STORMX - 8GB GDDR6 (NE65050019P1-GB2070F) (3Y)', 'Brands	PALIT\r\nGPU Series	NVIDIA GeForce RTX™ 50 Series\r\nGPU Model	GeForce® RTX 5050\r\nMemory Size	8GB GDDR6\r\nBus Standards	PCI-E 5.0\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	2560\r\nMemory Interface	128-bit\r\nBoost Clock	2572 MHz\r\nMemory Clock	20.0 Gbps\r\nMax Digital Resolution	\r\n3840 x 2160 @480Hz\r\n7680 x 4320 @120Hz\r\nHDMI Port	1 x HDMI 2.1b\r\nDisplay Port	3x DisplayPort™ (2.1b)\r\nPower Connector	1 x 8-pin\r\nPower Requirement	550 Watt\r\nDimension	169.9 x 118 x 39.8 mm\r\nWarranty	3 Years', 8890.00, 0, 0, 0, 999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products118662_800.jpg'),
('gpu08', 'VGA(การ์ดจอ) COLORFUL IGAME GEFORCE RTX 5050 ULTRA W DUO OC - 8GB GDDR6 (3Y)', 'Brands	COLORFUL\r\nGPU Series	NVIDIA GeForce RTX™ 50 Series\r\nGPU Model	GeForce® RTX 5050\r\nMemory Size	8GB GDDR6\r\nBus Standards	PCI Express® Gen 5\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	2560\r\nMemory Interface	128-bit\r\nBoost Clock	\r\n2647 MHz (One-Key OC)\r\n2572 MHz\r\nBase Clock	2317 MHz\r\nMemory Clock	20.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	1 x HDMI 2.1b\r\nDisplay Port	3x DisplayPort™ (2.1b)\r\nPower Connector	1 x 8-pin\r\nPower Requirement	550 Watt\r\nDimension	231 x 120 x 49 mm\r\nWarranty	3 Years', 9490.00, 0, 0, 0, 9999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products113230_800.jpg'),
('gpu09', 'VGA(การ์ดจอ) GIGABYTE GEFORCE RTX 5050 WINDFORCE OC 8G - 8GB GDDR6 (GV-N5050WF2OC-8GD) (3Y)', 'Brands	GIGABYTE\r\nGPU Series	NVIDIA GeForce RTX™ 50 Series\r\nGPU Model	GeForce® RTX 5050\r\nMemory Size	8GB GDDR6\r\nBus Standards	PCI-E 5.0\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	2560\r\nMemory Interface	128-bit\r\nBoost Clock	2587 MHz\r\nMemory Clock	20.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	2 x HDMI 2.1b\r\nDisplay Port	2x DisplayPort™ (2.1b)\r\nPower Connector	1 x 8-pin\r\nPower Requirement	550 Watt\r\nDimension	199 x 116 x 40 mm\r\nWarranty	3 Years', 9490.00, 0, 0, 0, 999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products118707_800.jpg'),
('gpu10', 'VGA(การ์ดจอ) GIGABYTE GEFORCE RTX 5050 GAMING OC 8G - 8GB GDDR6 (GV-N5050GAMING OC-8GD) (3Y)', 'Brands	GIGABYTE\r\nGPU Series	NVIDIA GeForce RTX™ 50 Series\r\nGPU Model	GeForce® RTX 5050\r\nMemory Size	8GB GDDR6\r\nBus Standards	PCI-E 5.0\r\nOpenGL	OpenGL® 4.6\r\nCUDA® Cores	2560\r\nMemory Interface	128-bit\r\nBoost Clock	2587 MHz\r\nMemory Clock	20.0 Gbps\r\nMax Digital Resolution	7680 x 4320\r\nHDMI Port	2 x HDMI 2.1b\r\nDisplay Port	\r\n1x DisplayPort™ 1.4a\r\n1x DisplayPort™ (2.1b)\r\nPower Connector	1 x 8-pin\r\nPower Requirement	550 Watt\r\nDimension	182 x 69 x 36 mm\r\nWarranty	3 Years', 9790.00, 0, 0, 0, 999, 'c03', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products118747_800.jpg'),
('lq01', 'LIQUID COOLER (ชุดน้ำปิด) ID-COOLING FX 240 PRO WHITE (3Y)', 'Brands	ID-COOLING\r\nCooler Model	FX 240 PRO\r\nExterior Color	WHITE\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nLGA 2011\r\nLGA 2066\r\nLGA 115x\r\nRadiator Dimensions	276 x 120 x 27 cm\r\nRadiator Material	Aluminum\r\nBlock Material	Copper\r\nRadiator Size	240 mm\r\nPump Speed	2900±10%RPM\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	500~1800 RPM±10%\r\nFan Airflow	82.5CFM\r\nFan Noise	35.2 dB(A)\r\nFan Connector	4-Pin (PWM)\r\nTDP	300W\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	3 Years', 2090.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products71107_800.jpg'),
('lq02', 'LIQUID COOLER (ชุดน้ำปิด) COOLER MASTER MASTERLIQUID 240L CORE ARGB (BLACK)', 'Cooler Brand	COOLER MASTER\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-1151\r\nIntel® LGA-1150\r\nIntel® LGA-1155\r\nIntel® LGA-1156\r\nAMD AM4\r\nAMD AM3+\r\nAMD AM3\r\nAMD AM2+\r\nAMD AM2\r\nAMD AM5\r\nRadiator Dimensions	277 x 119.6 x 27.2 mm\r\nPump Dimensions	81 x 76 x 47 mm / 3.2 x 3 x1.9 inch\r\nPump Speed	N/A\r\nFan Dimensions	120 x 120 x 25 mm\r\nTube Dimension	N/A\r\nFan LED Type	ARGB\r\nFan Speed	650~1750 RPM±10%\r\nFan Airflow	71.93 CFM\r\nFan Quantity	2 x 120mm\r\nFan Noise	27. 2dB(A)\r\nFan Connector	4-Pin (PWM)\r\nCooler Option	N/A\r\nCooler Type	Liquid Cooler\r\nWarranty	3 Years', 2290.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product32250_800.jpg'),
('lq03', 'LIQUID COOLER (ชุดน้ำปิด) COOLER MASTER MASTERLIQUID 240L CORE ARGB (WHITE)', 'Cooler Model	MASTERLIQUID 240L CORE ARGB\r\nCPU Socket	\r\nIntel® LGA-1700\r\nIntel® LGA-1200\r\nIntel® LGA-1151\r\nIntel® LGA-1150\r\nIntel® LGA-1155\r\nIntel® LGA-1156\r\nAMD AM4\r\nAMD AM3+\r\nAMD AM3\r\nAMD AM2+\r\nAMD AM2\r\nAMD AM5\r\nIntel® LGA-1851\r\nRadiator Dimensions	277 x 119.6 x 27.2 mm\r\nPump Dimensions	81 x 76 x 47 mm / 3.2 x 3 x1.9 inch\r\nPump Speed	N/A\r\nFan Dimensions	120 x 120 x 25 mm\r\nTube Dimension	N/A\r\nFan LED Type	ARGB\r\nFan Speed	650~1750 RPM±10%\r\nFan Airflow	71.93 CFM\r\nFan Quantity	3 x 120mm\r\nFan Noise	27. 2dB(A)\r\nFan Connector	4-Pin (PWM)\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	3 Years', 2290.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product33215_800.png'),
('lq04', 'LIQUID COOLER (ชุดน้ำปิด) MSI MAG CORELIQUID A13 240 (3Y)', 'Brands	MSI\r\nCooler Model	MAG CORELIQUID A13 240\r\nExterior Color	BLACK\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1700\r\nLGA 1851\r\nRadiator Dimensions	277 x 119.6 x 27mm / 10.91 x 4.69 x 1.06 inches\r\nRadiator Material	Aluminum\r\nBlock Material	N/A\r\nRadiator Size	240 mm\r\nPump Dimensions	N/A\r\nPump Speed	3800 RPM ±10%\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB Gen2\r\nFan Speed	N/A\r\nFan Airflow	62.6 CFM\r\nFan MTTF	40,000 Hours\r\nFan Noise	N/A\r\nFan Connector	5V ARGB header - 3 PIN\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	3 Years', 2390.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products91481_800.jpg'),
('lq05', 'LIQUID COOLER (ชุดน้ำปิด) GIGABYTE GAMING 240 (3Y)', 'Brands	GIGABYTE\r\nCooler Model	GAMING 240\r\nExterior Color	BLACK\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nLGA 115x\r\nRadiator Dimensions	284 x 120 x 35 mm\r\nRadiator Material	Aluminum\r\nBlock Material	Copper\r\nRadiator Size	240 mm\r\nPump Dimensions	66 x 66 x 63 mm\r\nPump Speed	4500 RPM±10%\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB\r\nFan Speed	500~2200 RPM +/-10%\r\nFan Airflow	61.61 CFM\r\nFan MTTF	N/A\r\nFan Noise	13.8 ~ 35.8 dBA\r\nFan Connector	4-Pin (PWM)\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	3 Years', 2390.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products101260_800.jpg'),
('lq06', 'LIQUID COOLER (ชุดน้ำปิด) MSI MAG CORELIQUID A13 240 WHITE (3Y)', 'Brands	MSI\r\nCooler Model	MAG CORELIQUID A13 240\r\nExterior Color	WHITE\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1700\r\nLGA 1851\r\nRadiator Dimensions	277 x 119.6 x 27mm / 10.91 x 4.69 x 1.06 inches\r\nRadiator Material	Aluminum\r\nRadiator Size	240 mm\r\nPump Dimensions	N/A\r\nPump Speed	3800 RPM ±10%\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB Gen2\r\nFan Speed	N/A\r\nFan Airflow	62.6 CFM\r\nFan MTTF	40,000 Hours\r\nFan Noise	N/A\r\nFan Connector	5V ARGB header - 3 PIN\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	3 Years', 2490.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products91501_800.jpg'),
('lq07', 'LIQUID COOLER (ชุดน้ำปิด) GIGABYTE GAMING 240 ICE (3Y)', 'Brands	GIGABYTE\r\nCooler Model	GAMING 240\r\nExterior Color	WHITE\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nLGA 115x\r\nRadiator Dimensions	284 x 120 x 35 mm\r\nRadiator Material	Aluminum\r\nBlock Material	Copper\r\nRadiator Size	240 mm\r\nPump Dimensions	66 x 66 x 63 mm\r\nPump Speed	4500 RPM±10%\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB\r\nFan Speed	500~2200 RPM +/-10%\r\nFan Airflow	61.61 CFM\r\nFan MTTF	N/A\r\nFan Noise	13.8 ~ 35.8 dBA\r\nFan Connector	4-Pin (PWM)\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	3 Years', 2490.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products101314_800.jpg'),
('lq08', 'LIQUID COOLER (ชุดน้ำปิด) ID-COOLING DX240 MAX BLACK (5Y)', 'Brands	ID-COOLING\r\nCooler Model	DX240 MAX\r\nExterior Color	BLACK\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nLGA 115x\r\nRadiator Dimensions	280 x 120 x 38 mm\r\nRadiator Material	Aluminum\r\nBlock Material	Copper\r\nRadiator Size	240 mm\r\nPump Dimensions	73 x 72 x 58 mm\r\nPump Speed	2900±10%RPM\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB\r\nFan Speed	2150±10%RPM\r\nFan Airflow	85 CFM\r\nFan MTTF	N/A\r\nFan Noise	32.5 dB(A)\r\nFan Connector	4-Pin (PWM)\r\nTDP	300W\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	5 Years', 2590.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products84886_800.jpg'),
('lq09', 'LIQUID COOLER (ชุดน้ำปิด) ID-COOLING DX240 MAX WHITE (5Y)', 'Brands	ID-COOLING\r\nCooler Model	DX240 MAX\r\nExterior Color	WHITE\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nLGA 115x\r\nRadiator Dimensions	280 x 120 x 38 mm\r\nRadiator Material	Aluminum\r\nBlock Material	Copper\r\nRadiator Size	240 mm\r\nPump Dimensions	73 x 72 x 58 mm\r\nPump Speed	2900±10%RPM\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB\r\nFan Speed	2150±10%RPM\r\nFan Airflow	85 CFM\r\nFan MTTF	N/A\r\nFan Noise	32.5 dB(A)\r\nFan Connector	4-Pin (PWM)\r\nTDP	300W\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	5 Years', 2690.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products84880_800.jpg'),
('lq10', 'LIQUID COOLER (ชุดน้ำปิด) COOLER MASTER MASTERLIQUID 240 CORE II ARGB (WHITE) (MLW-D24M-A18PA-RW) (5Y)', 'Brands	COOLER MASTER\r\nCooler Model	MASTERLIQUID 240 CORE II ARGB\r\nExterior Color	WHITE\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1150\r\nLGA 1151\r\nLGA 1155\r\nLGA 1156\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nRadiator Dimensions	277 x 119 x 27 mm\r\nRadiator Material	Aluminum\r\nRadiator Size	240 mm\r\nPump Dimensions	83 x 76.2 x 52.3 mm\r\nPump Speed	3100 RPM±10%\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB\r\nFan Speed	650~1750 RPM±10%\r\nFan Airflow	70.7 CFM\r\nFan MTTF	>160,000 Hours\r\nFan Noise	30 dB(A)\r\nFan Connector	7-Pin PWM + ARGB\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	5 Years', 2790.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products124075_800.jpg'),
('lq11', 'LIQUID COOLER (ชุดน้ำปิด) COOLER MASTER MASTERLIQUID 240 CORE II ARGB (BLACK) (MLW-D24M-A18PA-R1) (5Y)', 'Brands	COOLER MASTER\r\nCooler Model	MASTERLIQUID 240 CORE II ARGB\r\nExterior Color	BLACK\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1150\r\nLGA 1151\r\nLGA 1155\r\nLGA 1156\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nRadiator Dimensions	277 x 119 x 27 mm\r\nRadiator Material	Aluminum\r\nRadiator Size	240 mm\r\nPump Dimensions	83 x 76.2 x 52.3 mm\r\nPump Speed	3100 RPM±10%\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan LED Type	ARGB\r\nFan Speed	650~1750 RPM±10%\r\nFan Airflow	70.7 CFM\r\nFan MTTF	>160,000 Hours\r\nFan Noise	30 dB(A)\r\nFan Connector	7-Pin PWM + ARGB\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	5 Years', 2790.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products124083_800.jpg'),
('lq12', 'LIQUID COOLER (ชุดน้ำปิด) OCYPUS IOTA L24 WHITE (IOTA-L24-WH2ANWNN00X-GL) (5Y)', 'Brands	OCYPUS\r\nCooler Model	LOTA L24\r\nExterior Color	WHITE\r\nCPU Socket	\r\nAM4\r\nAM5\r\nLGA 1200\r\nLGA 1700\r\nLGA 1851\r\nLGA 115x\r\nRadiator Dimensions	276 x 120 x 27 cm\r\nRadiator Material	Aluminum\r\nRadiator Size	240 mm\r\nPump Dimensions	70 x 70 x 65 mm\r\nPump Speed	3100 RPM±10%\r\nFan Dimensions	120 x 120 x 25 mm\r\nFan Quantity	2 PCS\r\nFan Speed	500~2000 RPM±10%\r\nFan Airflow	77 CFM\r\nFan Noise	29 dB(A)\r\nFan Connector	4-Pin (PWM)\r\nWeight	1.23 kg\r\nCooler Type	CPU Liquid Cooler\r\nWarranty	5 Years', 2890.00, 0, 0, 0, 999, 'c08', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products118330_800.jpg'),
('m01', 'M.2 (เอสเอสดี) LEXAR x iHAVECPU NM620 256GB PCIe/NVMe GEN3x4 (LNM620X256G-RNNBG)', 'Form Factor	M.2 2280\r\nCapacity	256GB\r\nInterface	PCI Express 3.0\r\nRead Speed	3,500 MB/s\r\nWrite Speed	1,300 MB/s\r\nWarranty	5 Years', 770.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product38704_800.png'),
('m02', 'M.2 (เอสเอสดี) WD BLUE SN5000 500GB PCIe/NVMe GEN4 (WDS500G4B0E-00CNZ0) (5Y)', 'Brand	WD\r\nForm Factor	M.2 2280\r\nCapacity	500GB\r\nInterface	PCI Express 4.0\r\nRead Speed	5,000 MB/s\r\nWrite Speed	4,000 MB/s\r\nWarranty	5 Years', 1390.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products106573_800.jpg'),
('m03', 'M.2 (เอสเอสดี) LEXAR NQ790 500GB PCIe/NVMe GEN4x4 (LNQ790X500G-RNNNG) (5Y)', 'Brand	LEXAR\r\nForm Factor	M.2 2280\r\nCapacity	500GB\r\nInterface	PCI Express 4.0\r\nRead Speed	6,400 MB/s\r\nWrite Speed	2,900 MB/s\r\nWarranty	5 Years', 1590.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products81960_800.jpg'),
('m04', 'M.2 (เอสเอสดี) LEXAR NQ780 512GB PCIe/NVMe GEN4x4 (LNQ780X512G-RNNG) (5Y)', 'Brand	LEXAR\r\nForm Factor	M.2 2280\r\nCapacity	512GB\r\nInterface	PCI Express 4.0\r\nRead Speed	5000 MB/s\r\nWrite Speed	2,500 MB/s\r\nWarranty	5 Years', 1590.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products123852_800.jpg'),
('m05', 'M.2 (เอสเอสดี) KINGSTON NV3 1TB PCIe 4/NVMe M.2 2280 (SNV3S/1000G) (5Y)', 'Brand	KINGSTON\r\nForm Factor	M.2 2280\r\nCapacity	1TB\r\nInterface	PCI Express 4.0\r\nRead Speed	6,000 MB/s\r\nWrite Speed	4,000 MB/s\r\nWarranty	5 Years', 2090.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products60202_800.jpg'),
('m06', 'M.2 (เอสเอสดี) WD BLUE SN5000 1TB PCIe/NVMe GEN4 (WDS100T4B0E) (5Y)', 'Brand	WD\r\nForm Factor	M.2 2280\r\nCapacity	1TB\r\nInterface	PCI Express 4.0\r\nRead Speed	5,150 MB/s\r\nWrite Speed	4,900 MB/s\r\nWarranty	5 Years', 2190.00, 0, 0, 0, 9999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products106565_800.jpg'),
('m07', 'M.2 (เอสเอสดี) LEXAR NQ780 1TB PCIe/NVMe GEN4x4 (LNQ780XT001T- RNNG) (5Y)', 'Brand	LEXAR\r\nForm Factor	M.2 2280\r\nCapacity	1TB\r\nInterface	PCI Express 4.0\r\nRead Speed	6,500 MB/s\r\nWrite Speed	2,500 MB/s\r\nWarranty	5 Years', 2290.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products114846_800.jpg'),
('m08', 'M.2 (เอสเอสดี) KINGSTON NV3 2TB PCIe 4/NVMe M.2 2280 (SNV3S/2000G) (5Y)', 'Brand	KINGSTON\r\nForm Factor	M.2 2280\r\nCapacity	2TB\r\nInterface	PCI Express 4.0\r\nRead Speed	6,000 MB/s\r\nWrite Speed	5,000 MB/s\r\nWarranty	5 Years', 4490.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products67522_800.jpg'),
('m09', 'M.2 (เอสเอสดี) WD BLUE SN5000 2TB PCIe/NVMe GEN4x4 (WDS200T4B0E)', 'Brand	WD\r\nForm Factor	M.2 2280\r\nCapacity	2TB\r\nInterface	PCI Express 4.0\r\nRead Speed	5,000 MB/s\r\nWrite Speed	4,000 MB/s\r\nWarranty	5 Years', 4490.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products81964_800.jpg'),
('m10', 'M.2 (เอสเอสดี) LEXAR NQ790 2TB PCIe/NVMe GEN4x4 (LNQ790X002T-RNNNG) (5Y)', 'Brand	LEXAR\r\nForm Factor	M.2 2280\r\nCapacity	2TB\r\nInterface	PCI Express 4.0\r\nRead Speed	7,000 MB/s\r\nWrite Speed	6,000 MB/s\r\nWarranty	5 Years', 4790.00, 0, 0, 0, 999, 'c05', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products81964_800.jpg'),
('mb01', 'MAINBOARD (เมนบอร์ด)(AM4) ASROCK A520M-HVS', 'Brands	ASROCK\r\nCPU Support	\r\nAMD Ryzen 3000 G-Series\r\nAMD Ryzen 3000 Series\r\nAMD Ryzen 4000 G-Series\r\nAMD Ryzen 5000 G-Series\r\nAMD Ryzen 5000 Series\r\nCPU Socket	AM4\r\nChipset	AMD A520\r\nMemory Slots	2 x DIMM\r\nMemory Type	DDR4\r\nMax Memory	64GB\r\nOnboard Graphics	Integrated Graphic on Processor\r\nOnboard Audio Chipset	Realtek ALC887/897\r\nAudio Channels	7.1 CH HD Audio\r\nExpansion Slots	\r\n1 x PCIe 3.0 x16 Slot\r\n1 x PCIe 3.0 x1 Slot\r\nStorage	\r\n4 x SATA3 6Gb/s port(s)\r\n1 x M.2 Socket\r\nRear Panel I/O	\r\n1 x PS/2 Keyboard/Mouse port\r\n1 x HDMI™ port\r\n4 x USB 3.2 Gen 1 ports\r\n2 x USB 2.0 ports\r\n1 x LAN port\r\n1 x D-Sub port\r\n3 x Audio jacks\r\nLAN Chipset	Realtek RTL8111H\r\nLAN Speed	10/100/1000 Mbps\r\nDimensions	23.0 cm x 20.1 cm\r\nPower Pin	24+4 Pin\r\nForm Factor	Micro-ATX\r\nWarranty	3 Years', 1490.00, 0, 0, 0, 9999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product7282_800.jpg'),
('mb02', 'MAINBOARD (เมนบอร์ด)(AM4) MSI A520M-A-PRO', 'Brands	MSI\r\nCPU Support	\r\nAMD Ryzen 3000 G-Series\r\nAMD Ryzen 3000 Series\r\nAMD Ryzen 4000 Series\r\nAMD Ryzen 5000 G-Series\r\nAMD Ryzen 5000 Series\r\nCPU Socket	AM4\r\nChipset	AMD A520\r\nMemory Slots	2 x DIMM\r\nMemory Type	DDR4\r\nMax Memory	64GB\r\nOnboard Graphics	Integrated Graphic on Processor\r\nOnboard Audio Chipset	Realtek ALC892/ALC897 Codec\r\nAudio Channels	7.1-Channel High Definition Audio\r\nExpansion Slots	\r\n1 x PCIe 3.0 x16 Slot\r\n1 x PCIe 3.0 x1 Slot\r\nStorage	\r\n4 x SATA3 6Gb/s port(s)\r\n1 x M.2 Socket\r\nRear Panel I/O	\r\n1 x PS/2 Keyboard/Mouse port\r\n1 x HDMI™ port\r\n4 x USB 3.2 Gen 1 ports\r\n2 x USB 2.0 ports\r\n1 x LAN port\r\n3 x Audio jacks\r\n1 x DVI-D port\r\nLAN Chipset	Realtek RTL8111H\r\nLAN Speed	10/100/1000 Mbps\r\nDimensions	23.6 cm x 20.0 cm\r\nPower Pin	24+4 Pin\r\nForm Factor	Micro-ATX\r\nWarranty	3 Years', 1490.00, 0, 0, 0, 9999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product7422_800.jpg'),
('mb03', 'MAINBOARD (เมนบอร์ด)(AM4) GIGABYTE A520M K V2 (REV.1.1)', '', 1490.00, 0, 0, 0, 9999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products42896_800.jpg'),
('mb04', 'MAINBOARD (เมนบอร์ด)(AM5) ASUS PRIME A620M-K', 'Brands	ASUS\r\nCPU Support	\r\nAMD Ryzen 9000 Series\r\nAMD Ryzen 8000 Series\r\nAMD Ryzen 7000 Series\r\nCPU Socket	AM5\r\nChipset	AMD A620\r\nMemory Slots	2 x DIMM\r\nMemory Type	DDR5\r\nMax Memory	96GB\r\nOnboard Graphics	Requires a CPU With Integrated Graphics.\r\nOnboard Audio Chipset	Realtek Audio CODEC\r\nAudio Channels	7.1 Surround Sound High Definition Audio\r\nExpansion Slots	\r\n1 x PCIe 4.0 x16 Slot\r\n1 x PCIe 3.0 x1 Slot\r\nStorage	\r\n4 x SATA3 6Gb/s port(s)\r\n1 x M.2 Socket\r\nRear Panel I/O	\r\n1 x PS/2 Keyboard/Mouse port\r\n1 x HDMI™ port\r\n4 x USB 3.2 Gen 1 ports\r\n2 x USB 2.0 ports\r\n1 x VGA port\r\n1 x Realtek 1Gb Ethernet port\r\n3 x Audio jacks\r\nLAN Chipset	Realtek 1Gb Ethernet\r\nLAN Speed	10/100/1000 Mbps\r\nDimensions	22.6 cm x 22.1 cm\r\nPower Pin	24+8 Pin\r\nForm Factor	Micro-ATX\r\nWarranty	3 Years', 2290.00, 0, 0, 0, 9999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products81108_800.png'),
('mb05', 'MAINBOARD (เมนบอร์ด)(1700) ASUS PRIME H610M-E D4-CSM DDR4', 'Brands	ASUS\r\nCPU Support	\r\n14th Gen\r\n13th Gen\r\n12th Gen\r\nCPU Socket	LGA 1700\r\nChipset	Intel® H610\r\nMemory Slots	2 x DIMM\r\nMemory Type	DDR4\r\nMax Memory	64GB\r\nOnboard Graphics	Integrated Graphics Processor (Depends on CPU)\r\nOnboard Audio Chipset	Realtek\r\nAudio Channels	7.1 Surround Sound High Definition Audio\r\nExpansion Slots	\r\n1 x PCIe 4.0 x16 Slot\r\n1 x PCIe 3.0 x1 Slot\r\nStorage	\r\n4 x SATA3 6Gb/s port(s)\r\n2 x M.2 Socket\r\nRear Panel I/O	\r\n1 x DisplayPort\r\n1 x HDMI™ port\r\n2 x USB 3.2 Gen 1 ports\r\n2 x USB 2.0 ports\r\n1 x LAN port\r\n1 x D-Sub port\r\n3 x Audio jacks\r\n2 x PS/2 Keyboard/Mouse port\r\nLAN Chipset	Realtek 1Gb Ethernet\r\nLAN Speed	10/100/1000 Mbps\r\nDimensions	24.4 cm x 21.1 cm\r\nPower Pin	24+8 Pin\r\nForm Factor	Micro-ATX\r\nWarranty	3 Years', 2190.00, 0, 0, 0, 999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product12310_800.jpg');
INSERT INTO `products` (`product_id`, `p_name`, `p_description`, `p_price`, `price_advice`, `price_jib`, `price_ihavecpu`, `p_stock`, `cid`, `img_url`) VALUES
('mb06', 'MAINBOARD (เมนบอร์ด)(AM5) ASROCK B650M PG LIGHTNING DDR5 (3Y)', 'Brands	ASROCK\r\nCPU Support	\r\nAMD Ryzen 9000 Series\r\nAMD Ryzen 8000 Series\r\nAMD Ryzen 7000 Series\r\nCPU Socket	AM5\r\nChipset	AMD B650\r\nMemory Slots	4 x DIMM\r\nMemory Type	DDR5\r\nMax Memory	256GB\r\nOnboard Graphics	Requires a CPU With Integrated Graphics.\r\nOnboard Audio Chipset	Realtek ALC897 Codec\r\nAudio Channels	7.1 CH HD Audio\r\nExpansion Slots	\r\n1 x PCIe 4.0 x16 Slot\r\n1 x PCIe 3.0 x16 Slot\r\nStorage	\r\n4 x SATA3 6Gb/s port(s)\r\n3 x M.2 Socket\r\nRear Panel I/O	\r\n1 x DisplayPort\r\n1 x HDMI™ port\r\n4 x USB 2.0 ports\r\n3 x Audio jacks\r\n2 x Antenna Ports\r\n1 x RJ-45 port\r\n1 x Flash BIOS button\r\n2 x USB 3.2 Gen 1 Type-A ports\r\n1 x USB 10Gbps Type-A\r\n1 x USB 10Gbps Type-C\r\nLAN Chipset	Realtek Dragon RTL8125BG\r\nLAN Speed	10/100/1000/2500 Mbps\r\nDimensions	24.4 cm x 24.4 cm\r\nPower Pin	24+8 Pin\r\nForm Factor	Micro-ATX\r\nWarranty	3 Years', 3490.00, 0, 0, 0, 999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products77947_800.jpg'),
('mb07', 'MAINBOARD (เมนบอร์ด)(1700) GIGABYTE B760M AORUS ELITE AX DDR4 (REV.1.1) (3Y)', '', 3490.00, 0, 0, 0, 999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products127984_800.jpg'),
('mb08', 'MAINBOARD (เมนบอร์ด) (1700) ASUS PRIME B760M-A', 'Brands	ASUS\r\nCPU Support	\r\n14th Gen\r\n13th Gen\r\n12th Gen\r\nCPU Socket	LGA 1700\r\nChipset	Intel® B760\r\nMemory Slots	4 x DIMM\r\nMemory Type	DDR5\r\nMax Memory	128GB\r\nOnboard Graphics	Requires a CPU With Integrated Graphics.\r\nOnboard Audio Chipset	Realtek\r\nAudio Channels	7.1 Surround Sound High Definition Audio\r\nExpansion Slots	3 x PCI Express 4.0 x16 slots\r\nStorage	\r\n4 x SATA3 6Gb/s port(s)\r\n2 x M.2 Socket\r\nRear Panel I/O	\r\n1 x DisplayPort\r\n2 x HDMI™ ports\r\n4 x USB 2.0 ports\r\n1 x LAN port\r\n3 x Audio jacks\r\n1 x PS/2 Keyboard/Mouse combo port\r\n2 x USB 3.2 Gen 2 Type-A ports\r\nLAN Chipset	Realtek 2.5Gb Ethernet\r\nLAN Speed	100/1000/2500 Mbps\r\nDimensions	24.4 cm x 24.4 cm\r\nPower Pin	24+8 Pin\r\nForm Factor	Micro-ATX\r\nWarranty	3 Years', 3620.00, 0, 0, 0, 9999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products74850_800.jpg'),
('mb09', 'MAINBOARD (เมนบอร์ด)(AM5) ASROCK B650M PG LIGHTNING WIFI DDR5 (3Y)', '', 3690.00, 0, 0, 0, 9999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products46714_800.jpg'),
('mb10', 'MAINBOARD (เมนบอร์ด)(1700) ASROCK B760M PRO RS DDR5', 'Brands	ASROCK\r\nCPU Support	\r\n14th Gen\r\n13th Gen\r\n12th Gen\r\nCPU Socket	LGA 1700\r\nChipset	Intel® B760\r\nMemory Slots	4 x DIMM\r\nMemory Type	DDR5\r\nMax Memory	192GB\r\nOnboard Graphics	Intel® Xe Graphics Architecture (Gen 12)\r\nOnboard Audio Chipset	Realtek ALC892 Codec\r\nAudio Channels	7.1 CH HD Audio\r\nExpansion Slots	\r\n1 x PCIe 3.0 x16 Slot\r\n1 x PCIe 5.0 x16 Slot\r\nStorage	\r\n4 x SATA3 6Gb/s port(s)\r\n3 x M.2 Socket\r\nRear Panel I/O	\r\n1 x PS/2 Keyboard/Mouse port\r\n1 x DisplayPort\r\n1 x HDMI™ port\r\n2 x USB 2.0 ports\r\n2 x Antenna Mounting Points\r\n3 x Audio jacks\r\n1 x RJ-45 port\r\n1 x USB 3.2 Gen 2 Type-C Port\r\n3 x USB 3.2 Gen 1 Type-A ports\r\nLAN Chipset	Realtek Dragon RTL8125BG\r\nLAN Speed	10/100/1000/2500 Mbps\r\nDimensions	24.4 cm x 24.4 cm\r\nPower Pin	24+8 Pin\r\nForm Factor	Micro-ATX\r\nWarranty	3 Years', 3970.00, 0, 0, 0, 9999, 'c02', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products36576_800.png'),
('P69B2C249A199', 'Chris Redfield', 'Chris Redfield', 500000.00, 0, 0, 0, 0, 'c03', 'https://i.ytimg.com/an_webp/kjYmmtiTwgE/mqdefault_6s.webp?du=3000&sqp=CKr0ys0G&rs=AOn4CLBeRJ9vJYb6oe97lO4E2Y_y64NzpQ'),
('ps01', 'PSU (อุปกรณ์จ่ายไฟ) AEROCOOL UNITED POWER 600W (80+WHITE) (3Y)', 'Brand	AEROCOOL\r\nEnergy Efficient	80 PLUS WHITE\r\nModular	Non Modular\r\nContinuous Power W	600 Watt\r\nPSU Form Factor	ATX\r\nInput Current	4.5 A\r\nInput Frequency	47-63Hz\r\nMB Connector	1 x 20+4-pin\r\nCPU Connector	2 x 4+4-pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	4\r\nFan Size	120 mm\r\nDimensions W x D x H	150 x 140 x 86 mm\r\nWeight	1.28 KG\r\nWarranty	3 Years', 1190.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product9619_800.jpg'),
('ps02', 'PSU (อุปกรณ์จ่ายไฟ) AZZA PSAZ 550W (80+BRONZE) (3Y)', 'Brand	AZZA\r\nEnergy Efficient	80 PLUS BRONZE\r\nContinuous Power W	550 Watt\r\nPSU Form Factor	ATX\r\nInput Frequency	47-63Hz\r\nMB Connector	1 x 20+4-pin\r\nCPU Connector	1 x 4+4-Pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	5\r\nWarranty	3 Years', 1190.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product36175_800.png'),
('ps03', 'PSU (อุปกรณ์จ่ายไฟ) FSP HV+ 600W (80+WHITE) (3Y)', 'Brand	FSP\r\nEnergy Efficient	80 PLUS WHITE\r\nModular	Non Modular\r\nContinuous Power W	600 Watt\r\nForm Factor	ATX\r\nInput Voltage	200-240 V\r\nInput Current	4.5 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 24-pin\r\nCPU Connector	1 x 4+4-Pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	6\r\nFan Size	120 mm\r\nDimensions	140 x 150 x 86 mm\r\nProtections	Protection OPP/UVP/OVP/SCP/OCP\r\nWarranty	3 Years', 1190.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products91486_800.jpg'),
('ps04', 'PSU (อุปกรณ์จ่ายไฟ) MSI MAG A600DN 600W BULK (80+WHITE) (3Y) ไม่มีกล่อง', 'Brand	MSI\r\nEnergy Efficient	80 PLUS WHITE\r\nModular	Non Modular\r\nContinuous Power W	600 Watt\r\nForm Factor	ATX\r\nInput Voltage	100-240 V\r\nInput Current	10 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 24-pin\r\nCPU Connector	1 x 4+4-Pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	5\r\nFan Size	120 mm\r\nDimensions	150 x 140 x 86 mm\r\nProtections	Protection OCP/OVP/SCP/OPP\r\nWarranty	3 Years', 1290.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products106643_800.jpg'),
('ps05', 'PSU (อุปกรณ์จ่ายไฟ) GIGABYTE GP-P550SS 550W (80+SILVER) (3Y)', 'Brand	GIGABYTE\r\nEnergy Efficient	80 PLUS SILVER\r\nModular	Non Modular\r\nContinuous Power W	550 Watt\r\nForm Factor	ATX\r\nInput Voltage	155-240 V\r\nInput Current	6.3 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 20+4-pin\r\nCPU Connector	1 x 4+4-Pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	5\r\nFan Size	120 mm\r\nDimensions	150 x 140 x 86 mm\r\nProtections	OVP/OPP/SCP/UVP/OCP/OTP\r\nWarranty	3 Years', 1390.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products50833_800.jpg'),
('ps06', 'PSU (อุปกรณ์จ่ายไฟ) GIGABYTE GP-P550SS ICE 550W (80+SILVER) WHITE (3Y)', 'Brand	GIGABYTE\r\nEnergy Efficient	80 PLUS SILVER\r\nModular	Non Modular\r\nContinuous Power W	550 Watt\r\nForm Factor	ATX\r\nInput Voltage	155-240 V\r\nInput Current	6.3 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 20+4-pin\r\nCPU Connector	1 x 4+4-Pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	5\r\nFan Size	120 mm\r\nDimensions	140 x 150 x 86 mm\r\nProtections	OVP/OPP/SCP/UVP/OCP/OTP\r\nWarranty	3 Years', 1390.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products66171_800.jpg'),
('ps07', 'PSU (อุปกรณ์จ่ายไฟ) MSI MAG A650BN 650W (80+BRONZE)', 'Brand	MSI\r\nEnergy Efficient	80 PLUS BRONZE\r\nModular	Non Modular\r\nContinuous Power W	650 Watt\r\nPSU Form Factor	ATX\r\nInput Current	10 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 20+4-pin\r\nCPU Connector	1 x 4+4-Pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	5\r\nFan Size	120 mm\r\nDimensions W x D x H	140 x 150 x 86 mm\r\nWeight	1.7 Kg\r\nWarranty	5 Years', 1650.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product2371_800.jpg'),
('ps08', 'PSU (อุปกรณ์จ่ายไฟ) FSP HV PRO 85+ 650W 80+ BRONZE/DIRECT CABLE', 'Brand	FSP\r\nEnergy Efficient	80 PLUS BRONZE\r\nModular	Non Modular\r\nContinuous Power W	650 Watt\r\nForm Factor	ATX\r\nInput Voltage	200-240 V\r\nInput Current	5 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 24-pin\r\nCPU Connector	2 x 4+4-pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	5\r\nFan Size	120 mm\r\nDimensions	150 x 140 x 86 mm\r\nProtections	Protection OCP/OVP/SCP/OPP\r\nWarranty	3 Years', 1690.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products64789_800.png'),
('ps09', 'PSU (อุปกรณ์จ่ายไฟ) THERMALTAKE SMART BX1 650W (80+BRONZE) (5Y)', 'Brand	THERMALTAKE\r\nEnergy Efficient	80 PLUS BRONZE\r\nModular	Non Modular\r\nContinuous Power W	650 Watt\r\nForm Factor	ATX\r\nInput Voltage	100-240 V\r\nInput Current	12 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 24-pin\r\nCPU Connector	1 x 4+4-Pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	6\r\nFan Size	120 mm\r\nDimensions	150 x 140 x 86 mm\r\nWarranty	5 Years', 1690.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products46120_800.jpg'),
('ps10', 'PSU (อุปกรณ์จ่ายไฟ) GIGABYTE GP-P650SS 650W (80+SILVER) (3Y)', 'Brand	GIGABYTE\r\nEnergy Efficient	80 PLUS SILVER\r\nModular	Non Modular\r\nContinuous Power W	650 Watt\r\nForm Factor	ATX\r\nInput Voltage	155-240 V\r\nInput Current	6.3 A\r\nInput Frequency	50-60Hz\r\nMB Connector	1 x 20+4-pin\r\nCPU Connector	2 x 4+4-pin\r\nPCIe Connector	2 x 6+2-pin\r\nSATA Connector	5\r\nFan Size	120 mm\r\nDimensions	140 x 150 x 86 mm\r\nProtections	OVP/OPP/SCP/UVP/OCP/OTP\r\nWarranty	3 Years', 1790.00, 0, 0, 0, 999, 'c06', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products49254_800.jpg'),
('r01', 'RAM (แรม) GeIL ORION PHANTOM GAMING 16GB (8x2) DDR4 3200MHz GRAY (GAOG416GB3200C16BDC) (LT)', 'Brand	GEIL\r\nMemory Series	ORION\r\nMemory Capacity	16GB (2x 8GB)\r\nSpeed	3200MHz\r\nMemory Type	DDR4\r\nCas Latency	CL16\r\nSPD Voltage	1.20-1.35 V\r\nMemory Color	GRAY\r\nWarranty	Lifetime', 1590.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products73362_800.jpg'),
('r02', 'RAM (แรม) KLEVV BOLT X 16GB (8X2) DDR4 3200MHz (KD48GU880-32A160U) (LT)', 'Brand	KLEVV\r\nMemory Series	BOLT X\r\nMemory Capacity	16GB (2x 8GB)\r\nSpeed	3200MHz\r\nMemory Type	DDR4\r\nCas Latency	CL16\r\nTested Latency	16-18-18-38\r\nSPD Voltage	1.35 V\r\nMemory Color	BLACK\r\nWarranty	Lifetime', 1590.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products127478_800.jpg'),
('r03', 'RAM (แรม) CORSAIR VENGEANCE LPX 32GB (16x2) DDR4 3200MHz BLACK (CMK32GX4M2E3200C16)', 'Brand	CORSAIR\r\nMemory Series	VENGEANCE LPX\r\nMemory Capacity	32GB (16GBx2)\r\nCas Latency	CL16\r\nMemory Type	DDR4\r\nTested Latency	16-20-20-38\r\nSPD Voltage	1.35 V\r\nMemory Color	BLACK\r\nWarranty	Lifetime', 2990.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product2024_800.jpg'),
('r04', 'RAM (แรม) KINGSTON FURY BEAST 32GB (16x2) DDR5 5600MHz BLACK (KF556C40BBK2-32)', 'Brand	KINGSTON\r\nMemory Series	FURY BEAST RGB\r\nMemory Capacity	32GB (16GBx2)\r\nSpeed	5600MHz\r\nMemory Type	DDR5\r\nCas Latency	CL40\r\nTested Latency	40-40-40\r\nSPD Voltage	1.25 V\r\nMemory Color	BLACK\r\nWarranty	Lifetime', 3490.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/product7623_800.jpg'),
('r05', 'RAM (แรม) CORSAIR VENGEANCE 32GB (16x2) DDR5 5600MHz BLACK (CMK32GX5M2B5600C40) (LT)', 'Brand	CORSAIR\r\nMemory Series	VENGEANCE\r\nMemory Capacity	32GB (16GBx2)\r\nSpeed	5600MHz\r\nMemory Type	DDR5\r\nCas Latency	CL40\r\nTested Latency	40-40-40-77\r\nSPD Voltage	1.1 V\r\nMemory Color	BLACK\r\nWarranty	Lifetime', 3490.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products72762_800.jpg'),
('r06', 'RAM (แรม) CORSAIR VENGEANCE 32GB (16x2) DDR5 5600MHz WHITE (CMK32GX5M2B5600C40W) (LT)', 'Brand	CORSAIR\r\nMemory Series	VENGEANCE\r\nMemory Capacity	32GB (16GBx2)\r\nSpeed	5600MHz\r\nMemory Type	DDR5\r\nCas Latency	CL40\r\nTested Latency	40-40-40-77\r\nSPD Voltage	1.1 V\r\nMemory Color	WHITE\r\nWarranty	Lifetime', 3490.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products74088_800.jpg'),
('r07', 'RAM (แรม) KINGSTON FURY BEAST 32GB (16x2) DDR5 5600MHz WHITE (KF556C40BWK2-32) (LT)', 'Brand	KINGSTON\r\nMemory Series	FURY BEAST\r\nMemory Capacity	32GB (16GBx2)\r\nSpeed	5600MHz\r\nMemory Type	DDR5\r\nCas Latency	CL40\r\nTested Latency	40-40-40\r\nSPD Voltage	1.25 V\r\nMemory Color	WHITE\r\nWarranty	Lifetime', 3490.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products81972_800.png'),
('r08', 'RAM (แรม) KLEVV BOLT V 32GB (16x2) DDR5 6000MHz (PURE WHITE)(KD5AGUA80-60B280I) (LT)', 'Brand	KLEVV\r\nMemory Series	BOLT V\r\nMemory Capacity	32GB (2x 16GB)\r\nSpeed	6000MHz\r\nMemory Type	DDR5\r\nCas Latency	CL28\r\nTested Latency	28-36-36-76\r\nSPD Voltage	1.4 V\r\nMemory Color	PURE WHITE\r\nWarranty	Lifetime', 3990.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products127964_800.jpg'),
('r09', 'RAM (แรม) KLEVV BOLT V 32GB (16x2) DDR5 6000MHz (CHARCOAL GREY)(KD5AGUA80-60B280H) (LT)', 'Brand	KLEVV\r\nMemory Series	BOLT V\r\nMemory Capacity	32GB (2x 16GB)\r\nSpeed	6000MHz\r\nMemory Type	DDR5\r\nCas Latency	CL28\r\nTested Latency	28-36-36-76\r\nSPD Voltage	1.4 V\r\nMemory Color	CHARCOAL GREY\r\nWarranty	Lifetime', 3990.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products127963_800.jpg'),
('r10', 'RAM (แรม) HIKSEMI FUTURE RGB 32GB (16x2) DDR5 5600Mhz (BLACK)(HSC532U56C5) (LT)', 'Brand	HIKSEMI\r\nMemory Series	FUTURE RGB\r\nMemory Capacity	32GB (2x 16GB)\r\nSpeed	5600MHz\r\nMemory Type	DDR5\r\nMemory Color	BLACK\r\nWarranty	Lifetime', 3990.00, 0, 0, 0, 999, 'c04', 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products128120_800.jpg');

-- --------------------------------------------------------

--
-- Table structure for table `promotions`
--

CREATE TABLE `promotions` (
  `promo_id` varchar(15) NOT NULL,
  `promo_name` varchar(255) NOT NULL,
  `promo_description` text NOT NULL,
  `discount_type` enum('percent','fixed') NOT NULL,
  `discount_value` decimal(7,2) NOT NULL,
  `promo_stock` int(25) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `status` enum('active','inactive','expired') NOT NULL,
  `promo_price` decimal(20,2) NOT NULL,
  `promo_img` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `promotions`
--

INSERT INTO `promotions` (`promo_id`, `promo_name`, `promo_description`, `discount_type`, `discount_value`, `promo_stock`, `start_date`, `end_date`, `status`, `promo_price`, `promo_img`) VALUES
('CS001', 'AMD RYZEN 5 5500GT 3.6GHz 6C/12T / A520M / ONBOARD / 16GB DDR4 3200MHz / M.2 1TB / 550W (80+SILVER) / 21.5\" 100Hz', 'CPU	AMD Ryzen™ 5 5500GT 3.6GHz 6C/12T (3Y)\r\nMainboard	ASUS PRIME A520M-K (3Y)\r\nGraphic card	AMD RADEON GRAPHICS (อัพเกรดการ์ดจอติดต่อ ADMIN)\r\nMemory	GeIL ORION PHANTOM GAMING 16GB (8x2) DDR4 3200MHz GRAY (LT)\r\nStorage	M.2 KINGSTON NV3 1TB Read (6,000 MB/s) (5Y)\r\nPower Supply	GIGABYTE GP-P550SS 550W (80+ SILVER) (3Y)\r\nCase	iHAVECPU INFINITY MINI (BLACK)(mATX) (1Y) | (เลือกเคสติดต่อ ADMIN)\r\nMonitor	21.5\" / 1920 X 1080 (FHD) / FLAT / 100Hz', 'fixed', 2000.00, 100, '2025-10-01', '2025-10-31', 'active', 13490.00, 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products133787_800.jpg'),
('CS002', 'AMD RYZEN 5 5500GT 3.6GHz 6C/12T / A520M / ONBOARD / 16GB DDR4 3200MHz / M.2 1TB / 550W (80+SILVER) / 23.X\" 144Hz', 'CPU	AMD Ryzen™ 5 5500GT 3.6GHz 6C/12T (3Y)\r\nMainboard	ASUS PRIME A520M-K (3Y)\r\nGraphic card	AMD RADEON GRAPHICS (อัพเกรดการ์ดจอติดต่อ ADMIN)\r\nMemory	GeIL ORION PHANTOM GAMING 16GB (8x2) DDR4 3200MHz GRAY (LT)\r\nStorage	M.2 KINGSTON NV3 1TB Read (6,000 MB/s) (5Y)\r\nPower Supply	GIGABYTE GP-P550SS ICE 550W (80+SILVER) WHITE (3Y)\r\nCase	iHAVECPU INFINITY MINI (WHITE)(mATX) (1Y) | (เลือกเคสติดต่อ ADMIN)\r\nMonitor	23.X\" / 1920 X 1080 (FHD) / FLAT / 144Hz\r\n\r\n**ของแถม**\r\n    -    สติ๊กเกอร์ Computer Science\r\n\r\n    -    T-SHIRT Computer Science V20 (SIZE L)\r\n\r\n    -    USB WIFI D-LINK N150\r\n\r\n    -    คอมโบเช็ต iHAVECPU GAMING BUNDLE KIT V.2 (IHC-102)\r\n\r\n    -    กระเป๋า KINGSTON FOLDABLE BACKPACK\r\n\r\nของแถมมีจำนวนจำกัด', 'fixed', 2000.00, 20, '2025-10-01', '2025-10-31', 'active', 14990.00, 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products133790_800.jpg'),
('CS003', 'AMD RYZEN 5 5500GT 3.6GHz 6C/12T / A520M / ONBOARD / 16GB DDR4 3200MHz / M.2 1TB / 550W (80+SILVER) / 27.X\" 144Hz', 'CPU	AMD Ryzen™ 5 5500GT 3.6GHz 6C/12T (3Y)\r\nMainboard	ASUS PRIME A520M-K (3Y)\r\nGraphic card	AMD RADEON GRAPHICS (อัพเกรดการ์ดจอติดต่อ ADMIN)\r\nMemory	GeIL ORION PHANTOM GAMING 16GB (8x2) DDR4 3200MHz GRAY (LT)\r\nStorage	M.2 KINGSTON NV3 1TB Read (6,000 MB/s) (5Y)\r\nPower Supply	GIGABYTE GP-P550SS 550W (80+ SILVER) (3Y)\r\nCase	iHAVECPU CRYSTAL Z6 MINI (BLACK)(mATX) (1Y) | (เลือกเคสติดต่อ ADMIN)\r\nMonitor	27.X\" / 1920 X 1080 (FHD) / FLAT / 120Hz\r\n\r\n**ของแถม**\r\n    -    สติ๊กเกอร์ Computer Science\r\n\r\n    -    T-SHIRT Computer Science V20 (SIZE L)\r\n\r\n    -    USB WIFI D-LINK N150\r\n\r\n    -    คอมโบเช็ต iHAVECPU GAMING BUNDLE KIT V.2 (IHC-102)\r\n\r\n    -    กระเป๋า KINGSTON FOLDABLE BACKPACK\r\n\r\nของแถมมีจำนวนจำกัด', 'percent', 20.00, 20, '2025-10-01', '2025-10-31', 'active', 14990.00, 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products133793_800.jpg'),
('CS004', 'INTEL I5-12400 2.5GHz 6C/12T / H610M / ONBOARD / 16GB DDR4 3200MHz / M.2 1TB / 550W (80+SILVER) / 21.5\" 100Hz', 'CPU	Intel® CORE I5-12400 2.5GHz 6C/12T (3Y)\r\nMainboard	ASUS PRIME H610M-E D4-CSM (3Y)\r\nGraphic card	INTEL UHD GRAPHICS 730 (อัพเกรดการ์ดจอติดต่อ ADMIN)\r\nMemory	GeIL ORION PHANTOM GAMING 16GB (8x2) DDR4 3200MHz GRAY (LT)\r\nStorage	M.2 KINGSTON NV3 1TB Read (6,000 MB/s) (5Y)\r\nPower Supply	GIGABYTE GP-P550SS ICE 550W (80+SILVER) WHITE (3Y)\r\nCase	iHAVECPU CRYSTAL Z6 MINI (WHITE)(mATX) (1Y) | (เลือกเคสติดต่อ ADMIN)\r\nMonitor	21.5\" / 1920 X 1080 (FHD) / FLAT / 100Hz\r\n\r\n**ของแถม**\r\n    -    สติ๊กเกอร์ Computer Science\r\n\r\n    -    T-SHIRT Computer Science V20 (SIZE L)\r\n\r\n    -    USB WIFI D-LINK N150\r\n\r\n    -    คอมโบเช็ต iHAVECPU GAMING BUNDLE KIT V.2 (IHC-102)\r\n\r\n    -    กระเป๋า KINGSTON FOLDABLE BACKPACK\r\n\r\nของแถมมีจำนวนจำกัด', 'percent', 20.00, 25, '2025-10-01', '2025-10-31', 'active', 15190.00, 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products133796_800.jpg'),
('CS005', 'INTEL I5-12400 2.5GHz 6C/12T / H610M / ONBOARD / 16GB DDR4 3200MHz / M.2 1TB / 550W (80+SILVER) / 23.X\" 144Hz', 'CPU	Intel® CORE I5-12400 2.5GHz 6C/12T (3Y)\r\nMainboard	ASUS PRIME H610M-E D4-CSM (3Y)\r\nGraphic card	INTEL UHD GRAPHICS 730 (อัพเกรดการ์ดจอติดต่อ ADMIN)\r\nMemory	GeIL ORION PHANTOM GAMING 16GB (8x2) DDR4 3200MHz GRAY (LT)\r\nStorage	M.2 KINGSTON NV3 1TB Read (6,000 MB/s) (5Y)\r\nPower Supply	GIGABYTE GP-P550SS 550W (80+ SILVER) (3Y)\r\nCase	iHAVECPU CRYSTAL Z9 MINI (BLACK)(mATX) (1Y) | (เลือกเคสติดต่อ ADMIN)\r\nMonitor	23.X\" / 1920 X 1080 (FHD) / FLAT / 144Hz\r\n\r\n**ของแถม**\r\n    -    สติ๊กเกอร์ Computer Science\r\n\r\n    -    T-SHIRT Computer Science V20 (SIZE L)\r\n\r\n    -    USB WIFI D-LINK N150\r\n\r\n    -    คอมโบเช็ต iHAVECPU GAMING BUNDLE KIT V.2 (IHC-102)\r\n\r\n    -    กระเป๋า KINGSTON FOLDABLE BACKPACK\r\n\r\nของแถมมีจำนวนจำกัด', 'percent', 1500.00, 15, '2025-10-01', '2025-10-31', 'active', 16190.00, 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products133799_800.jpg'),
('CS006', 'INTEL I5-12400 2.5GHz 6C/12T / H610M / ONBOARD / 16GB DDR4 3200MHz / M.2 1TB / 550W (80+SILVER) / 27.X\" 144Hz', 'CPU	Intel® CORE I5-12400 2.5GHz 6C/12T (3Y)\r\nMainboard	ASUS PRIME H610M-E D4-CSM (3Y)\r\nGraphic card	INTEL UHD GRAPHICS 730 (อัพเกรดการ์ดจอติดต่อ ADMIN)\r\nMemory	GeIL ORION PHANTOM GAMING 16GB (8x2) DDR4 3200MHz GRAY (LT)\r\nStorage	M.2 KINGSTON NV3 1TB Read (6,000 MB/s) (5Y)\r\nPower Supply	GIGABYTE GP-P550SS ICE 550W (80+SILVER) WHITE (3Y)\r\nCase	iHAVECPU CRYSTAL Z9 MINI (WHITE)(mATX) (1Y) | (เลือกเคสติดต่อ ADMIN)\r\nMonitor	27.X\" / 1920 X 1080 (FHD) / FLAT / 120Hz\r\n\r\n**ของแถม**\r\n    -    สติ๊กเกอร์ Computer Science\r\n\r\n    -    T-SHIRT Computer Science V20 (SIZE L)\r\n\r\n    -    USB WIFI D-LINK N150\r\n\r\n    -    คอมโบเช็ต iHAVECPU GAMING BUNDLE KIT V.2 (IHC-102)\r\n\r\n    -    กระเป๋า KINGSTON FOLDABLE BACKPACK\r\n\r\nของแถมมีจำนวนจำกัด', 'fixed', 2500.00, 20, '2025-10-01', '2025-10-31', 'active', 16690.00, 'https://ihcupload.s3.ap-southeast-1.amazonaws.com/img/product/products133802_800.jpg'),
('CS10', 'CS Bro', 'comsci students only', 'fixed', 100.00, 1, '2025-11-01', '2025-11-30', 'active', 5000.00, 'https://cms.theuniguide.com/sites/default/files/2019-09/feature-article-tips-for-being-a-computer-science-student-at-university-838x484-2018.jpg');

-- --------------------------------------------------------

--
-- Table structure for table `promotion_products`
--

CREATE TABLE `promotion_products` (
  `pp_id` varchar(8) NOT NULL,
  `promo_id` varchar(8) NOT NULL,
  `product_id` varchar(8) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `promotion_products`
--

INSERT INTO `promotion_products` (`pp_id`, `promo_id`, `product_id`) VALUES
('', '0', 'cp09');

-- --------------------------------------------------------

--
-- Table structure for table `refunds`
--

CREATE TABLE `refunds` (
  `refund_id` varchar(8) NOT NULL,
  `return_id` varchar(8) NOT NULL,
  `payment_id` varchar(8) NOT NULL,
  `refund_amount` decimal(7,2) NOT NULL,
  `refund_date` date NOT NULL,
  `refund_status` enum('pending','processed','failed') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `returns`
--

CREATE TABLE `returns` (
  `return_id` varchar(8) NOT NULL,
  `order_id` varchar(8) NOT NULL,
  `product_id` varchar(8) NOT NULL,
  `r_reason` text NOT NULL,
  `r_status` enum('pending','approved','rejected','refunded') NOT NULL,
  `r_created_at` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reviews`
--

CREATE TABLE `reviews` (
  `reviews_id` varchar(8) NOT NULL,
  `product_id` varchar(8) NOT NULL,
  `uid` varchar(8) NOT NULL,
  `r_raiting` int(2) NOT NULL,
  `r_comment` text NOT NULL,
  `r_media_url` text NOT NULL,
  `r_helpful_count` int(7) NOT NULL,
  `r_verified_purchase` tinyint(1) NOT NULL,
  `review_status` enum('pending','approved','rejected') NOT NULL,
  `r_created_at` date NOT NULL,
  `r_updated_at` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `shipping`
--

CREATE TABLE `shipping` (
  `shipping_id` varchar(8) NOT NULL,
  `order_id` varchar(8) NOT NULL,
  `tracking_number` varchar(30) NOT NULL,
  `s_carrier` varchar(10) NOT NULL,
  `shipping_date` date NOT NULL,
  `s_status` enum('processing','in_transit','delivered') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `spec_history`
--

CREATE TABLE `spec_history` (
  `id` int(11) NOT NULL,
  `uid` varchar(50) NOT NULL,
  `username` varchar(100) NOT NULL,
  `type` varchar(20) NOT NULL,
  `mode` varchar(50) NOT NULL,
  `title` varchar(255) NOT NULL,
  `inputSummary` text NOT NULL,
  `result_data` longtext NOT NULL COMMENT 'เก็บข้อมูล JSON ของสเปค',
  `createdAt` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `spec_history`
--

INSERT INTO `spec_history` (`id`, `uid`, `username`, `type`, `mode`, `title`, `inputSummary`, `result_data`, `createdAt`) VALUES
(1, 'U69af9da', 'ntp1', 'ai', 'recommend', 'ใช้งานทั่วไป (ท่องเน็ต / ดูหนัง / เรียน) | 50,000 บาทขึ้นไป', 'ใช้งานทั่วไป (ท่องเน็ต / ดูหนัง / เรียน), 50,000 บาทขึ้นไป', '{\"summary\":\"คอมพิวเตอร์เครื่องนี้ถูกออกแบบมาเพื่อมอบประสบการณ์การใช้งานทั่วไปที่ลื่นไหลไร้ที่ติ พร้อมประสิทธิภาพที่ยอดเยี่ยมสำหรับการเล่นเกมที่ความละเอียด 1440p ด้วยกราฟิกการ์ด RTX 4070 SUPER และแพลตฟอร์ม AM5 ที่ทันสมัย.\",\"totalBudget\":\"52,200 ฿\",\"tier\":\"Mid-range to High-end\",\"parts\":[{\"type\":\"CPU\",\"name\":\"AMD Ryzen 5 7600\",\"price\":\"8,000 ฿\",\"reason\":\"เป็น CPU ที่คุ้มค่าที่สุดในแพลตฟอร์ม AM5 ให้ประสิทธิภาพ Single-core และ Multi-core ที่ยอดเยี่ยมสำหรับการใช้งานทั่วไป การเรียน และยังสามารถรับมือกับงานที่หนักขึ้นได้ดี มีความประหยัดพลังงานสูง และมี Integrated Graphics (RDNA2) ในตัว\"},{\"type\":\"Mainboard\",\"name\":\"ASUS PRIME B650M-A WIFI\",\"price\":\"6,500 ฿\",\"reason\":\"เมนบอร์ดชิปเซ็ต B650 รองรับ Socket AM5 สำหรับ CPU Ryzen 7000 Series มีฟีเจอร์ครบครันสำหรับราคา เช่น Wi-Fi 6, PCIe 4.0, DDR5 และ VRM ที่เพียงพอต่อการใช้งาน Ryzen 5 7600 พร้อมช่องทางอัปเกรดในอนาคต\"},{\"type\":\"RAM\",\"name\":\"Kingston FURY Beast RGB 32GB (2x16GB) DDR5 6000MHz CL36\",\"price\":\"4,500 ฿\",\"reason\":\"ขนาด 32GB เพียงพอและเหลือเฟือสำหรับการใช้งานทั่วไป การเปิดหลายแท็บ การเรียนออนไลน์ และยังรองรับงานที่ต้องการ RAM มากขึ้นได้ดี ความเร็ว 6000MHz CL36 เป็นจุดที่เหมาะสมที่สุดสำหรับ Ryzen 7000 Series เพื่อประสิทธิภาพสูงสุด\"},{\"type\":\"GPU\",\"name\":\"NVIDIA GeForce RTX 4070 SUPER 12GB (เช่น ZOTAC GAMING Twin Edge OC)\",\"price\":\"23,000 ฿\",\"reason\":\"แม้การใช้งานหลักจะเป็นงานทั่วไป แต่ด้วยงบประมาณที่สูง การ์ดจอรุ่นนี้จะมอบประสบการณ์ที่เหนือกว่าอย่างเห็นได้ชัด ไม่ว่าจะเป็นความลื่นไหลของ UI, การประมวลผลกราฟิกที่รวดเร็ว และยังสามารถเล่นเกม AAA ที่ความละเอียด 1440p ได้อย่างยอดเยี่ยมที่ High-Ultra settings พร้อมเทคโนโลยี DLSS 3 เพื่อเพิ่มเฟรมเรต\"},{\"type\":\"Storage\",\"name\":\"WD Black SN770 1TB NVMe PCIe Gen4\",\"price\":\"3,200 ฿\",\"reason\":\"SSD NVMe PCIe Gen4 ขนาด 1TB ให้ความเร็วในการอ่าน\\/เขียนข้อมูลที่สูงมาก ทำให้การเปิดเครื่อง เปิดโปรแกรม และโหลดไฟล์ต่างๆ เป็นไปอย่างรวดเร็ว พื้นที่ 1TB เพียงพอสำหรับการติดตั้งระบบปฏิบัติการ โปรแกรม และเก็บไฟล์มีเดียจำนวนมาก\"},{\"type\":\"PSU\",\"name\":\"Corsair RM750e (2023) 750W 80+ Gold\",\"price\":\"3,800 ฿\",\"reason\":\"PSU ขนาด 750W 80+ Gold ให้พลังงานที่เสถียรและมีประสิทธิภาพสูง เพียงพอสำหรับ CPU และ GPU ที่เลือกใช้ พร้อมเผื่อ headroom สำหรับการอัปเกรดในอนาคต และเป็นแบบ Fully Modular ช่วยให้จัดสายได้ง่ายขึ้น\"},{\"type\":\"Case\",\"name\":\"Montech AIR 903 MAX\",\"price\":\"2,200 ฿\",\"reason\":\"เคส Mid-Tower ที่เน้นการไหลเวียนอากาศที่ดีเยี่ยม มาพร้อมพัดลมคุณภาพสูงที่ติดตั้งมาให้ ช่วยระบายความร้อนได้ดีเยี่ยม ทำให้ส่วนประกอบภายในทำงานได้อย่างมีประสิทธิภาพและเงียบ\"},{\"type\":\"Cooler\",\"name\":\"Deepcool AK400\",\"price\":\"1,000 ฿\",\"reason\":\"ชุดระบายความร้อน CPU แบบ Air Cooler ที่มีประสิทธิภาพสูงกว่า Stock Cooler อย่างมาก ช่วยให้ Ryzen 5 7600 ทำงานได้อย่างเย็นและเงียบ แม้ในขณะโหลดหนักๆ\"}],\"performance\":{\"gaming\":\"สามารถเล่นเกม AAA ที่ความละเอียด 1440p ได้อย่างยอดเยี่ยมที่ High-Ultra settings โดยได้เฟรมเรต 60-100+ FPS ขึ้นอยู่กับเกม และสามารถเล่นเกม E-sports ที่ 1080p\\/1440p ได้เฟรมเรตสูงกว่า 144 FPS ได้อย่างสบายๆ รองรับ Ray Tracing และ DLSS 3 ได้ดี\",\"productivity\":\"ประสิทธิภาพสูงสำหรับการใช้งานทั่วไป เช่น การท่องเว็บ เปิดหลายแท็บ ดูหนัง 4K การเรียนออนไลน์ การทำงานเอกสาร และยังสามารถรองรับงานที่ต้องการทรัพยากรมากขึ้น เช่น การตัดต่อวิดีโอเบื้องต้น การเขียนโปรแกรม หรือการประมวลผลข้อมูลขนาดเล็กได้ดี\",\"upgrade\":\"สามารถอัปเกรด CPU ไปยัง Ryzen 7000\\/8000\\/9000 Series ที่จะออกในอนาคตได้ (ขึ้นอยู่กับการรองรับของเมนบอร์ดและ BIOS) สามารถเพิ่ม SSD NVMe หรือ SATA เพิ่มเติมได้ และสามารถอัปเกรด GPU ไปยังรุ่นที่สูงขึ้นในอนาคตได้ง่าย\"},\"pros\":[\"ประสิทธิภาพโดยรวมสูงมากสำหรับการใช้งานทั่วไปและเล่นเกม 1440p\",\"แพลตฟอร์ม AM5 ที่ทันสมัย มีช่องทางการอัปเกรด CPU ในอนาคต\",\"RAM DDR5 ขนาด 32GB เพียงพอสำหรับการใช้งานที่หลากหลายและมัลติทาสก์\",\"SSD NVMe Gen4 ที่รวดเร็ว ทำให้การโหลดโปรแกรมและไฟล์เป็นไปอย่างฉับไว\",\"PSU คุณภาพสูง 80+ Gold ให้พลังงานที่เสถียรและมีประสิทธิภาพ\",\"เคสมีการระบายอากาศที่ดีเยี่ยม ช่วยให้ระบบทำงานได้อย่างเย็นและเงียบ\"],\"cons\":[\"อาจจะเกินความจำเป็นไปบ้างหากลูกค้าใช้งานเพียงแค่ท่องเน็ต\\/ดูหนัง\\/เรียนเท่านั้น แต่ก็เป็นการลงทุนเพื่อความลื่นไหลและอนาคต\",\"ราคาอาจจะสูงกว่างบขั้นต่ำ 50,000 บาทเล็กน้อย แต่ยังอยู่ในช่วง \'50,000 บาทขึ้นไป\' และให้ประสิทธิภาพที่คุ้มค่ามาก\"]}', '2026-03-12 22:32:06'),
(2, 'U69af9da', 'ntp1', 'ai', 'recommend', 'เล่นเกม PC (AAA / Esports) | undefined', 'เล่นเกม PC (AAA / Esports), undefined', '{\"summary\":\"สเปคนี้คือเครื่องเล่นเกมระดับ High-end ที่ออกแบบมาเพื่อประสบการณ์ 1440p ที่ลื่นไหลและสวยงามในทุกเกม AAA และ Esports ด้วยการ์ดจอ RTX 4080 Super และ CPU Ryzen 7 7800X3D ที่เป็นที่สุดสำหรับการเล่นเกม.\",\"totalBudget\":\"75,500 ฿\",\"tier\":\"High-end Gaming (1440p Ultra \\/ Entry 4K)\",\"parts\":[{\"type\":\"CPU\",\"name\":\"AMD Ryzen 7 7800X3D\",\"price\":\"12,900 ฿\",\"reason\":\"เป็น CPU ที่ดีที่สุดสำหรับการเล่นเกมในปัจจุบัน (ณ ปี 2026) ด้วยเทคโนโลยี 3D V-Cache ที่ให้ประสิทธิภาพเกมที่เหนือกว่าคู่แข่งในราคาที่คุ้มค่า และยังคงความแรงไปได้อีกหลายปีข้างหน้า\"},{\"type\":\"Mainboard\",\"name\":\"GIGABYTE B650 AORUS ELITE AX V2\",\"price\":\"7,800 ฿\",\"reason\":\"เมนบอร์ด Socket AM5 ที่รองรับ Ryzen 7 7800X3D ได้อย่างสมบูรณ์แบบ ชิปเซ็ต B650 ให้ความคุ้มค่าสูง มี VRM ที่แข็งแกร่ง รองรับ PCIe Gen 4\\/5, DDR5 และมี Wi-Fi 6E ในตัว พร้อมพอร์ตเชื่อมต่อที่ครบครัน\"},{\"type\":\"RAM\",\"name\":\"G.Skill Flare X5 32GB (2x16GB) DDR5 6000MHz CL30\",\"price\":\"4,500 ฿\",\"reason\":\"หน่วยความจำขนาด 32GB เพียงพอสำหรับการเล่นเกม AAA ในปัจจุบันและอนาคต รวมถึงการทำงานทั่วไป ความเร็ว 6000MHz CL30 เป็นจุดที่เหมาะสมที่สุดสำหรับ AMD Ryzen 7000 series เพื่อประสิทธิภาพสูงสุดในการเล่นเกม\"},{\"type\":\"GPU\",\"name\":\"NVIDIA GeForce RTX 4080 Super\",\"price\":\"37,000 ฿\",\"reason\":\"การ์ดจอที่ให้ประสิทธิภาพยอดเยี่ยมสำหรับการเล่นเกมที่ความละเอียด 1440p Ultra settings ด้วย Ray Tracing และยังสามารถเล่นเกม 4K ได้ดีในหลายๆ เกม เหมาะสำหรับทั้งเกม AAA ที่ต้องการกราฟิกสูงสุดและเกม Esports ที่ต้องการเฟรมเรตสูง\"},{\"type\":\"Storage\",\"name\":\"Crucial P5 Plus 2TB NVMe PCIe Gen4\",\"price\":\"5,500 ฿\",\"reason\":\"พื้นที่จัดเก็บขนาด 2TB เพียงพอสำหรับลงเกม AAA จำนวนมากและระบบปฏิบัติการ PCIe Gen4 ให้ความเร็วในการอ่าน\\/เขียนข้อมูลที่สูงมาก ช่วยลดเวลาโหลดเกมและเข้าถึงไฟล์ต่างๆ ได้อย่างรวดเร็ว\"},{\"type\":\"PSU\",\"name\":\"Corsair RM850e (2023) 850W 80 PLUS Gold\",\"price\":\"4,200 ฿\",\"reason\":\"พาวเวอร์ซัพพลายขนาด 850W ให้กำลังไฟที่เพียงพอและมี headroom สำหรับ RTX 4080 Super และ Ryzen 7 7800X3D เพื่อการทำงานที่เสถียร 80 PLUS Gold รับรองประสิทธิภาพการจ่ายไฟสูงและประหยัดพลังงาน เป็นแบบ Fully Modular ช่วยให้จัดสายได้ง่าย\"},{\"type\":\"Case\",\"name\":\"Montech AIR 903 MAX\",\"price\":\"2,300 ฿\",\"reason\":\"เคสที่มีการออกแบบเน้นการไหลเวียนอากาศที่ดีเยี่ยม มาพร้อมพัดลมขนาดใหญ่ด้านหน้า 200mm สองตัวและด้านหลัง 140mm หนึ่งตัว ช่วยระบายความร้อนให้กับส่วนประกอบภายในได้อย่างมีประสิทธิภาพ มีพื้นที่กว้างขวางสำหรับติดตั้งอุปกรณ์และจัดการสายเคเบิล\"},{\"type\":\"Cooler\",\"name\":\"Deepcool LS520 SE 240mm AIO Liquid Cooler\",\"price\":\"3,300 ฿\",\"reason\":\"ชุดระบายความร้อนด้วยน้ำแบบ All-in-One ขนาด 240mm ที่ให้ประสิทธิภาพการระบายความร้อนที่ดีเยี่ยมสำหรับ Ryzen 7 7800X3D ช่วยให้ CPU ทำงานที่อุณหภูมิต่ำและเงียบ แม้ในขณะเล่นเกมหนักๆ\"}],\"performance\":{\"gaming\":\"เล่นเกมที่ความละเอียด 1440p Ultra settings: คาดหวัง 80-120+ FPS ในเกม AAA ที่ต้องการทรัพยากรสูง (เช่น Cyberpunk 2077, Alan Wake 2 พร้อม Ray Tracing), 120-180+ FPS ในเกม AAA ทั่วไป (เช่น Forza Horizon 5, Spider-Man Remastered) และ 240+ FPS ในเกม Esports (เช่น Valorant, CS2, Apex Legends) สามารถเล่นเกม 4K ได้ดีในหลายๆ เกม\",\"productivity\":\"ประสิทธิภาพดีเยี่ยมสำหรับงานทั่วไป, การสร้างคอนเทนต์ระดับเริ่มต้นถึงกลาง (เช่น ตัดต่อวิดีโอ 1080p\\/1440p, สตรีมเกม) ด้วย CPU ที่มีประสิทธิภาพสูงและ RAM ขนาด 32GB\",\"upgrade\":\"สามารถอัปเกรด CPU เป็นรุ่น Zen 5 X3D ในอนาคตบนแพลตฟอร์ม AM5 ได้, อัปเกรด GPU เป็นการ์ดจอรุ่นใหม่ในอนาคต (เช่น RTX 5080\\/5090 หรือเทียบเท่า) เมื่อมีวางจำหน่าย, เพิ่ม SSD NVMe หรือ SATA ได้อีกหลายตัว\"},\"pros\":[\"ประสิทธิภาพการเล่นเกม 1440p ที่ยอดเยี่ยมและลื่นไหล\",\"CPU ที่ดีที่สุดสำหรับการเล่นเกมในตลาด\",\"แพลตฟอร์ม AM5 ที่รองรับการอัปเกรดในอนาคต\",\"RAM และ Storage เพียงพอสำหรับเกมและงานปัจจุบัน\",\"ระบบระบายความร้อนและการไหลเวียนอากาศที่ดีเยี่ยม\",\"PSU ที่มีคุณภาพและกำลังไฟเพียงพอ\"],\"cons\":[\"ราคาสูงสำหรับการลงทุนเริ่มต้น\",\"อาจจะเกินความจำเป็นหากเล่นแค่เกม 1080p เท่านั้น\"]}', '2026-03-12 22:38:56'),
(3, 'U69af9da', 'ntp1', 'ai', 'recommend', 'เล่นเกม PC (AAA / Esports) | undefined', 'เล่นเกม PC (AAA / Esports), undefined', '{\"summary\":\"ชุดคอมพิวเตอร์สำหรับเล่นเกมระดับ Mid-range ที่เน้นความคุ้มค่าสูงสุดในงบประมาณที่ยืดหยุ่น โดดเด่นด้วยการ์ดจอ AMD Radeon RX 7600 และ CPU AMD Ryzen 5 5600 ที่ให้ประสิทธิภาพยอดเยี่ยมสำหรับการเล่นเกม AAA ที่ 1080p\\/1440p และเกม Esports ที่เฟรมเรตสูง.\",\"totalBudget\":\"22,080 ฿\",\"tier\":\"Mid-range\",\"parts\":[{\"type\":\"CPU\",\"name\":\"AMD Ryzen 5 5600 3.5GHz 6C 12T\",\"price\":\"2,990 ฿\",\"reason\":\"เป็น CPU ที่คุ้มค่าที่สุดสำหรับการเล่นเกมในงบประมาณนี้ ด้วย 6 คอร์ 12 เธรด ให้ประสิทธิภาพการเล่นเกมที่ยอดเยี่ยมเทียบเท่าหรือดีกว่า Intel Core i5-12400F แต่มีราคาที่ถูกกว่ามาก ทำให้ประหยัดงบประมาณไปลงกับการ์ดจอได้มากขึ้น ควรซื้อที่ Advice หรือ JIB เพราะราคาเท่ากัน.\"},{\"type\":\"Mainboard\",\"name\":\"MSI A520M-A-PRO (AM4)\",\"price\":\"1,490 ฿\",\"reason\":\"เมนบอร์ดชิปเซ็ต A520M เป็นตัวเลือกที่ประหยัดและเพียงพอต่อการใช้งานกับ Ryzen 5 5600 ที่ไม่รองรับการ Overclocking รองรับ DDR4 และมีฟีเจอร์พื้นฐานครบครันสำหรับระบบเกมมิ่งระดับกลาง ควรซื้อที่ Advice หรือ JIB.\"},{\"type\":\"RAM\",\"name\":\"CORSAIR VENGEANCE LPX 32GB (16x2) DDR4 3200MHz BLACK (CMK32GX4M2E3200C16)\",\"price\":\"2,990 ฿\",\"reason\":\"แรมขนาด 32GB (16GBx2) เป็นขนาดที่เหมาะสมที่สุดสำหรับการเล่นเกม AAA ในปัจจุบันและอนาคต รวมถึงการทำงาน multitask ต่างๆ ความเร็ว 3200MHz เป็นจุดที่คุ้มค่าที่สุดสำหรับ DDR4 บนแพลตฟอร์ม AM4 ช่วยให้ Ryzen 5 5600 ทำงานได้เต็มประสิทธิภาพ ควรซื้อที่ Advice หรือ JIB.\"},{\"type\":\"GPU\",\"name\":\"XFX SPEEDSTER SWFT210 RADEON RX 7600 CORE - 8GB GDDR6 (RX-76PSWFTFY)\",\"price\":\"8,290 ฿\",\"reason\":\"การ์ดจอที่คุ้มค่าที่สุดในงบประมาณนี้ ให้ประสิทธิภาพการเล่นเกมที่ยอดเยี่ยมที่ความละเอียด 1080p และ 1440p สามารถเล่นเกม AAA ได้ที่ High-Ultra settings และเกม Esports ได้ที่เฟรมเรตสูงมาก เหนือกว่า RTX 3050 อย่างชัดเจนในราคาที่ใกล้เคียงกัน ควรซื้อที่ Advice หรือ JIB.\"},{\"type\":\"Storage\",\"name\":\"WD BLUE SN5000 1TB PCIe\\/NVMe GEN4 (WDS100T4B0E)\",\"price\":\"2,190 ฿\",\"reason\":\"SSD M.2 NVMe Gen4 ขนาด 1TB ให้ความเร็วในการโหลดเกมและระบบปฏิบัติการที่รวดเร็วทันใจ เป็นขนาดที่เพียงพอสำหรับติดตั้งเกมและโปรแกรมจำนวนมาก WD Blue เป็นแบรนด์ที่เชื่อถือได้ในด้านคุณภาพและความทนทาน ควรซื้อที่ Advice หรือ JIB.\"},{\"type\":\"PSU\",\"name\":\"MSI MAG A650BN 650W (80+BRONZE)\",\"price\":\"1,650 ฿\",\"reason\":\"PSU ขนาด 650W พร้อมมาตรฐาน 80+ Bronze ให้กำลังไฟที่เสถียรและมีประสิทธิภาพเพียงพอสำหรับ CPU และ GPU ในสเปคนี้ (รวมกันประมาณ 250-300W) มี headroom เหลือเฟือสำหรับการอัปเกรดในอนาคต MSI เป็นแบรนด์ที่น่าเชื่อถือ ควรซื้อที่ Advice หรือ JIB.\"},{\"type\":\"Case\",\"name\":\"iHAVECPU G390 V2 (BLACK)(mATX)\",\"price\":\"1,490 ฿\",\"reason\":\"เคสขนาด mATX ที่รองรับเมนบอร์ดที่เลือก มีดีไซน์ที่เรียบง่ายและเน้นการระบายอากาศที่ดีในราคาที่คุ้มค่า ช่วยให้ส่วนประกอบภายในทำงานได้อย่างมีประสิทธิภาพ ควรซื้อที่ iHaveCPU.\"},{\"type\":\"Cooler\",\"name\":\"DEEPCOOL AK400 BLACK\",\"price\":\"990 ฿\",\"reason\":\"ซิงค์ลมที่คุ้มค่าที่สุดในตลาดสำหรับ CPU ระดับกลาง ให้ประสิทธิภาพการระบายความร้อนที่ดีกว่าซิงค์เดิมของ Ryzen 5 5600 อย่างเห็นได้ชัด ทำให้ CPU ทำงานได้เย็นและเงียบยิ่งขึ้นภายใต้โหลดหนักๆ ควรซื้อที่ Advice หรือ JIB.\"}],\"performance\":{\"gaming\":\"สามารถเล่นเกม AAA ล่าสุดที่ความละเอียด 1080p ปรับ High-Ultra settings ได้ที่ 60+ FPS และบางเกมอาจถึง 90-100+ FPS เช่น Cyberpunk 2077 (High), Alan Wake 2 (Medium-High). สำหรับเกม Esports เช่น Valorant, CS2, Apex Legends สามารถทำได้ 144+ FPS ได้อย่างสบายๆ ที่ 1080p Ultra settings. ที่ความละเอียด 1440p สามารถเล่นเกม AAA ได้ที่ Medium-High settings ที่ 40-60+ FPS.\",\"productivity\":\"ด้วย CPU 6 คอร์ 12 เธรด และ RAM 32GB ทำให้เหมาะสำหรับการทำงานทั่วไป, การตัดต่อวิดีโอ Full HD เบื้องต้น, การทำงานกราฟิก 2D และการใช้งานโปรแกรมที่ต้องใช้ทรัพยากรหลายอย่างพร้อมกันได้ดี.\",\"upgrade\":\"ในอนาคตสามารถอัปเกรด CPU เป็น Ryzen 7 5700X3D หรือ 5800X3D บนเมนบอร์ด AM4 เดิมเพื่อประสิทธิภาพการเล่นเกมที่สูงขึ้นได้อีกมาก หรืออัปเกรดการ์ดจอเป็นรุ่นที่สูงขึ้น เช่น RX 7700 XT \\/ RTX 4060 Ti เพื่อประสิทธิภาพ 1440p ที่ดียิ่งขึ้น.\"},\"pros\":[\"ประสิทธิภาพการเล่นเกมต่อราคา (Performance-per-Baht) สูงมาก โดยเฉพาะ RX 7600\",\"RAM 32GB เพียงพอสำหรับการเล่นเกมและทำงานในปัจจุบันและอนาคต\",\"ระบบระบายความร้อน CPU เพียงพอและเงียบกว่า Stock Cooler\",\"ใช้ SSD NVMe Gen4 ขนาด 1TB ที่รวดเร็ว\",\"PSU มีกำลังไฟเพียงพอและมี headroom สำหรับการอัปเกรด\"],\"cons\":[\"แพลตฟอร์ม AM4 ไม่มีเส้นทางการอัปเกรด CPU ไปสู่รุ่นใหม่ๆ ในอนาคต (เช่น Ryzen 8000\\/9000 series) เหมือน AM5\",\"เมนบอร์ด A520M มีฟีเจอร์พื้นฐาน อาจไม่เหมาะสำหรับผู้ที่ต้องการพอร์ตเชื่อมต่อหรือฟังก์ชันพิเศษจำนวนมาก\"]}', '2026-03-12 23:02:12'),
(4, 'U69af9da', 'ntp1', 'ai', 'recommend', 'ทำงานออฟฟิศ (Office / Video Call) | 15,000–20,000 บาท', 'ทำงานออฟฟิศ (Office / Video Call), 15,000–20,000 บาท', '{\"summary\":\"สเปคคอมพิวเตอร์สำหรับการทำงานออฟฟิศและวิดีโอคอลที่คุ้มค่าและทันสมัย ด้วยแพลตฟอร์ม AM5 ล่าสุด พร้อมหน่วยประมวลผลกราฟิกในตัวที่ทรงพลัง และ RAM DDR5 ขนาด 32GB เพื่อการทำงานที่ลื่นไหลและรองรับการอัปเกรดในอนาคต\",\"totalBudget\":\"16,790 ฿\",\"tier\":\"Entry-level \\/ Mid-range (สำหรับงาน Office)\",\"parts\":[{\"type\":\"CPU\",\"name\":\"AMD AM5 RYZEN 5 8500G 3.5GHz 6C 12T\",\"price\":\"5390.00 ฿\",\"reason\":\"ซีพียูรุ่นใหม่บนแพลตฟอร์ม AM5 ที่มี 6 คอร์ 12 เธรด ประสิทธิภาพสูงสำหรับการทำงานออฟฟิศและมัลติทาสก์ มาพร้อมกราฟิก Radeon 740M ในตัวที่ทรงพลังเพียงพอสำหรับงานทั่วไปและวิดีโอคอล ไม่จำเป็นต้องมีการ์ดจอแยก ช่วยประหยัดงบประมาณ\"},{\"type\":\"Mainboard\",\"name\":\"MAINBOARD (เมนบอร์ด)(AM5) ASUS PRIME A620M-K\",\"price\":\"2290.00 ฿\",\"reason\":\"เมนบอร์ด AM5 ราคาประหยัดที่รองรับซีพียู Ryzen 8000G series และ RAM DDR5 ได้อย่างสมบูรณ์แบบ มีพอร์ตเชื่อมต่อที่จำเป็นสำหรับการใช้งานทั่วไป\"},{\"type\":\"RAM\",\"name\":\"KINGSTON FURY BEAST 32GB (16x2) DDR5 5600MHz BLACK (KF556C40BBK2-32)\",\"price\":\"3490.00 ฿\",\"reason\":\"แรมขนาด 32GB (แบบ Dual Channel) เพียงพอและเหลือเฟือสำหรับการทำงานออฟฟิศหนักๆ การเปิดหลายโปรแกรมพร้อมกัน และการประชุมวิดีโอคอลที่ราบรื่น DDR5 5600MHz ยังช่วยเพิ่มประสิทธิภาพให้กับกราฟิกในตัวของซีพียู\"},{\"type\":\"GPU\",\"name\":\"Integrated Radeon 740M Graphics (จาก CPU)\",\"price\":\"0 ฿\",\"reason\":\"กราฟิกในตัวของ AMD Ryzen 5 8500G มีประสิทธิภาพดีเยี่ยมสำหรับการแสดงผลงานออฟฟิศ การดูหนัง และการประชุมวิดีโอคอล ไม่จำเป็นต้องมีการ์ดจอแยก ช่วยให้ประหยัดงบประมาณได้อย่างมาก\"},{\"type\":\"Storage\",\"name\":\"WD BLUE SN5000 1TB PCIe\\/NVMe GEN4 (WDS100T4B0E)\",\"price\":\"2190.00 ฿\",\"reason\":\"SSD แบบ NVMe PCIe Gen4 ขนาด 1TB ให้ความเร็วในการอ่าน-เขียนข้อมูลสูง ทำให้การเปิดเครื่อง เปิดโปรแกรม และการถ่ายโอนไฟล์เป็นไปอย่างรวดเร็ว 1TB เป็นขนาดที่เพียงพอสำหรับระบบปฏิบัติการ โปรแกรม และไฟล์งานจำนวนมาก\"},{\"type\":\"PSU\",\"name\":\"AZZA PSAZ 550W (80+BRONZE)\",\"price\":\"1190.00 ฿\",\"reason\":\"พาวเวอร์ซัพพลายขนาด 550W พร้อมมาตรฐาน 80+ Bronze ให้กำลังไฟที่เพียงพอและมีเสถียรภาพสำหรับระบบนี้ และมีประสิทธิภาพในการแปลงพลังงานที่ดี\"},{\"type\":\"Case\",\"name\":\"CASE (เคส) iHAVECPU IHC R06 ARGB (WHITE)(mATX)\",\"price\":\"1350.00 ฿\",\"reason\":\"เคสขนาด mATX ที่เข้ากับเมนบอร์ด มีดีไซน์ที่ทันสมัยพร้อมไฟ ARGB และมีช่องระบายอากาศที่ดี ช่วยให้การไหลเวียนของอากาศภายในเคสมีประสิทธิภาพ\"},{\"type\":\"Cooler\",\"name\":\"AIR COOLER (ซิงค์ลม) ID-COOLING SE-214-XT-PLUS\",\"price\":\"890.00 ฿\",\"reason\":\"ชุดระบายความร้อนซีพียูแบบลมที่มีประสิทธิภาพดีกว่าพัดลมสต็อกที่มาพร้อมกับซีพียู ช่วยให้ซีพียูทำงานได้เย็นและเงียบขึ้น โดยเฉพาะเมื่อมีการใช้งานหนักต่อเนื่อง\"}],\"performance\":{\"gaming\":\"สามารถเล่นเกม E-sports ทั่วไป (เช่น League of Legends, Valorant, CS:GO) ที่ความละเอียด 1080p ปรับกราฟิกระดับ Low-Medium ได้อย่างลื่นไหล และเกม AAA เก่าๆ ที่ปรับกราฟิกต่ำสุดได้\",\"productivity\":\"ยอดเยี่ยมสำหรับการทำงานออฟฟิศทุกประเภท การเปิดโปรแกรม Office หลายตัวพร้อมกัน การประชุมวิดีโอคอลคุณภาพสูง การเปิดแท็บเบราว์เซอร์จำนวนมาก และงานมัลติทาสก์ต่างๆ จะทำได้อย่างราบรื่นและรวดเร็ว\",\"upgrade\":\"สามารถอัปเกรดซีพียูเป็นรุ่นที่สูงขึ้นในอนาคตบนแพลตฟอร์ม AM5 ได้ (เช่น Ryzen 7, Ryzen 9) และสามารถเพิ่มการ์ดจอแยกได้หากต้องการเล่นเกมที่กราฟิกสูงขึ้นหรือทำงานด้านกราฟิกหนักๆ โดยอาจต้องพิจารณาอัปเกรด PSU หากเป็นการ์ดจอระดับสูงมาก\"},\"pros\":[\"ประสิทธิภาพยอดเยี่ยมสำหรับงานออฟฟิศและวิดีโอคอล\",\"แพลตฟอร์ม AM5 ที่ทันสมัย รองรับเทคโนโลยีล่าสุดและมีเส้นทางการอัปเกรดที่ดีเยี่ยมในอนาคต\",\"RAM DDR5 ขนาด 32GB ที่เพียงพอต่อการใช้งานหนักและรองรับอนาคต\",\"SSD NVMe Gen4 ขนาด 1TB ที่รวดเร็วและมีพื้นที่เก็บข้อมูลมาก\",\"ประหยัดงบประมาณด้วยกราฟิกในตัวที่ทรงพลัง ไม่ต้องซื้อการ์ดจอแยก\"],\"cons\":[\"กราฟิกในตัวไม่เหมาะสำหรับการเล่นเกม AAA สมัยใหม่ที่ปรับกราฟิกสูง หรือการทำงานกราฟิก\\/3D ระดับมืออาชีพ\",\"เมนบอร์ด A620M เป็นรุ่นเริ่มต้น อาจมีฟีเจอร์หรือพอร์ตเชื่อมต่อที่จำกัดกว่าเมนบอร์ดชิปเซ็ต B650\"]}', '2026-03-12 23:15:26'),
(5, 'U69af9da', 'ntp1', 'ai', 'recommend', 'เล่นเกม PC (AAA / Esports) | undefined', 'เล่นเกม PC (AAA / Esports), undefined', '{\"summary\":\"สเปคคอมพิวเตอร์สำหรับการเล่นเกม PC (AAA \\/ Esports) ที่เน้นความคุ้มค่าสูงสุดบนแพลตฟอร์ม AM5 ที่ทันสมัย พร้อมการ์ดจอ RTX 5050 เพื่อประสบการณ์การเล่นเกมที่ลื่นไหลในระดับ 1080p และ 1440p.\",\"totalBudget\":\"26,940 ฿\",\"tier\":\"Entry-level to Mid-range\",\"parts\":[{\"type\":\"CPU\",\"name\":\"AMD AM5 RYZEN 5 8400F 4.2GHz 6C 12T (MPK) (3Y)\",\"price\":\"4290.00 ฿\",\"reason\":\"เป็น CPU AM5 ที่คุ้มค่าที่สุดในงบประมาณ ให้ประสิทธิภาพที่ดีสำหรับการเล่นเกมและงานทั่วไป พร้อมรองรับการอัปเกรดในอนาคตบนแพลตฟอร์ม AM5\"},{\"type\":\"Mainboard\",\"name\":\"MAINBOARD (เมนบอร์ด)(AM5) ASROCK B650M PG LIGHTNING DDR5 (3Y)\",\"price\":\"3490.00 ฿\",\"reason\":\"เมนบอร์ด B650M ที่มีราคาเข้าถึงได้ รองรับ CPU AM5 และ RAM DDR5 ได้เต็มประสิทธิภาพ มีฟีเจอร์ที่จำเป็นครบครันสำหรับการเล่นเกม\"},{\"type\":\"RAM\",\"name\":\"KINGSTON FURY BEAST 32GB (16x2) DDR5 5600MHz BLACK (KF556C40BBK2-32)\",\"price\":\"3490.00 ฿\",\"reason\":\"ขนาด 32GB เพียงพอสำหรับการเล่นเกม AAA และ Esports ในปี 2026 และความเร็ว 5600MHz เป็นจุดที่คุ้มค่าสำหรับ DDR5\"},{\"type\":\"GPU\",\"name\":\"VGA(การ์ดจอ) GIGABYTE GEFORCE RTX 5050 WINDFORCE OC 8G - 8GB GDDR6 (GV-N5050WF2OC-8GD) (3Y)\",\"price\":\"9490.00 ฿\",\"reason\":\"การ์ดจอที่คุ้มค่าที่สุดในงบประมาณสำหรับการเล่นเกม PC (AAA \\/ Esports) ในปี 2026 ให้ประสิทธิภาพที่ดีเยี่ยมในระดับ 1080p และสามารถเล่น 1440p ได้ในบางเกม\"},{\"type\":\"Storage\",\"name\":\"M.2 (เอสเอสดี) WD BLUE SN5000 1TB PCIe\\/NVMe GEN4 (WDS100T4B0E) (5Y)\",\"price\":\"2190.00 ฿\",\"reason\":\"SSD NVMe PCIe Gen4 ขนาด 1TB ให้ความเร็วในการโหลดเกมและโปรแกรมที่รวดเร็ว เพียงพอสำหรับการติดตั้งเกมจำนวนมาก\"},{\"type\":\"PSU\",\"name\":\"PSU (อุปกรณ์จ่ายไฟ) MSI MAG A650BN 650W (80+BRONZE)\",\"price\":\"1650.00 ฿\",\"reason\":\"แหล่งจ่ายไฟ 650W 80+ Bronze ที่มีคุณภาพ ให้พลังงานเพียงพอและมี headroom สำหรับ CPU และ GPU ที่เลือกใช้\"},{\"type\":\"Case\",\"name\":\"CASE (เคส) iHAVECPU IHC R06 ARGB (WHITE)(mATX) (1Y)\",\"price\":\"1350.00 ฿\",\"reason\":\"เคส mATX ที่ออกแบบมาให้มี airflow ที่ดี พร้อมพัดลม ARGB เพิ่มความสวยงามและช่วยระบายความร้อนได้อย่างมีประสิทธิภาพ\"},{\"type\":\"Cooler\",\"name\":\"AIR COOLER (ซิงค์ลม) DEEPCOOL AK400 BLACK (3Y)\",\"price\":\"990.00 ฿\",\"reason\":\"ซิงค์ลมประสิทธิภาพสูงในราคาที่คุ้มค่า สามารถระบายความร้อน CPU Ryzen 5 8400F ได้อย่างสบายๆ แม้ในขณะเล่นเกมหนัก\"}],\"performance\":{\"gaming\":\"สามารถเล่นเกม AAA ส่วนใหญ่ที่ความละเอียด 1080p ปรับ High-Ultra settings ได้ที่ 100+ FPS และ 1440p ปรับ Medium-High settings ได้ที่ 60+ FPS สำหรับเกม Esports จะได้เฟรมเรตสูงมาก (200+ FPS) ที่ 1080p\",\"productivity\":\"ประสิทธิภาพดีเยี่ยมสำหรับงานทั่วไป, การท่องเว็บ, งานเอกสาร, การเรียนออนไลน์, และงานสร้างสรรค์คอนเทนต์เบื้องต้น รวมถึงการสตรีมเกมเบาๆ\",\"upgrade\":\"สามารถอัปเกรด CPU เป็น Ryzen 7 หรือ Ryzen 9 รุ่นใหม่บนแพลตฟอร์ม AM5 ได้ในอนาคต, สามารถอัปเกรดการ์ดจอที่แรงขึ้นได้โดย PSU 650W ยังพอรองรับการ์ดจอรุ่นกลาง-สูงได้, และสามารถเพิ่ม SSD M.2 หรือ SATA ได้อีก\"},\"pros\":[\"แพลตฟอร์ม AM5 ที่ทันสมัย รองรับการอัปเกรดในอนาคต\",\"การ์ดจอ RTX 5050 ให้ประสิทธิภาพการเล่นเกมที่ดีเยี่ยมในราคาที่คุ้มค่า\",\"RAM 32GB DDR5 เพียงพอสำหรับทุกการใช้งานและการเล่นเกม AAA ในปัจจุบันและอนาคตอันใกล้\",\"SSD NVMe Gen4 โหลดเกมและโปรแกรมได้รวดเร็ว ลดเวลารอคอย\",\"ระบบระบายความร้อน CPU เพียงพอและมีประสิทธิภาพ ทำให้ CPU ทำงานได้เต็มที่\"],\"cons\":[\"เมนบอร์ดเป็นรุ่น mATX อาจมีข้อจำกัดในการเพิ่ม Expansion Card บางประเภทในอนาคต\",\"PSU 650W อาจจำกัดการอัปเกรดการ์ดจอระดับ High-end มากๆ ในอนาคต (แต่เพียงพอสำหรับ mid-range)\",\"RTX 5050 อาจมี VRAM 8GB ซึ่งอาจเป็นข้อจำกัดสำหรับเกม AAA ที่ความละเอียด 1440p+ ในอนาคตอันไกลโพ้น\"]}', '2026-03-12 23:16:47');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `uid` varchar(8) NOT NULL,
  `u_name` varchar(155) NOT NULL,
  `u_email` varchar(155) NOT NULL,
  `u_password` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `u_phone` varchar(12) NOT NULL,
  `u_address` text DEFAULT NULL,
  `u_image` varchar(255) DEFAULT NULL,
  `dob` date NOT NULL,
  `u_role` enum('customer','admin') NOT NULL DEFAULT 'customer',
  `u_created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `u_updated_at` datetime NOT NULL,
  `u_last_login` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`uid`, `u_name`, `u_email`, `u_password`, `u_phone`, `u_address`, `u_image`, `dob`, `u_role`, `u_created_at`, `u_updated_at`, `u_last_login`) VALUES
('u001', 'alp', 'zfrankenz123@gmail.com', '$2y$10$isfbcdvkNp5zsfn4VFm/o.DBe7rXcjuoOlADo61uwtL8Icd2R52ni', '0111111111', NULL, NULL, '2004-12-10', 'admin', '2025-10-04 01:36:30', '0000-00-00 00:00:00', '2025-10-10 02:33:31'),
('u002', 'ntp', 'example1@gmail.com', '$2y$10$2fmDMRZ7Vv0dMK1hDrkxmurQVMJ1H3JEqrZmJAlIPfGFH2rLaH0R2', '', NULL, NULL, '2025-11-06', 'customer', '2025-10-10 02:30:50', '0000-00-00 00:00:00', '2025-10-10 02:31:22'),
('u008', 'post', 'Post@gmail.com', '$2y$10$3oqmzlgN4Az6IAYVHQ/vDu9w24VqNfkRg7CKOWTp2pi65aBwrdgdy', '00198451111', '99/34', 'u008_1761062966.jpg', '2548-04-25', 'customer', '2025-10-21 20:07:03', '0000-00-00 00:00:00', '2025-10-21 20:19:15'),
('u009', 'kaoru', 'Kaoru@gmail.com', '$2y$10$0NSCQcy//6QikMFVALkI1uAb4vTzs95UsVUa9dGBUcqlgjK9UonvG', '0011100011', NULL, NULL, '2005-05-18', 'customer', '2025-10-20 21:30:20', '0000-00-00 00:00:00', '0000-00-00 00:00:00'),
('u011', 'koko', 'Koko@gmail.com', '$2y$10$oFTV63SUBpbFwKYg2O9PUu2hbjg48YhduaNtLTbgZ9N01WZvhBVdS', '00198422222', NULL, NULL, '2008-05-18', 'customer', '2025-10-21 20:57:13', '0000-00-00 00:00:00', '0000-00-00 00:00:00'),
('u025', 'kaoruy', 'kaoruy@gmail.com', '$2y$10$kMS2obCiOh6fTm5U3QG7AeFYbAZOk3qboatDaq8SzgOqx8e9OBp5W', '08888888888', '99/58 asdfklkjf', 'u025_1761103258.jpg', '2007-04-28', 'customer', '2025-10-22 09:50:52', '0000-00-00 00:00:00', NULL),
('u123', 'uraiwan2', 'uraiwan@gmail.com', '$2y$10$IS5xwtUlhgl3VNEKtc6TqOT4XKDl2DhvtcrvVeQfCj2HwVV7ws.3m', '0123456789', '23', NULL, '2005-05-12', 'customer', '2025-11-01 10:52:54', '0000-00-00 00:00:00', NULL),
('U69af9da', 'ntp1', 'dfghjk@gmail.com', '$2y$10$l6CM/ULrkS.8pjsQ/6LkeOrckoI/nC7me4AUaw5RvfC6H2y.b4shG', '0123456789', NULL, NULL, '2026-03-10', 'admin', '2026-03-10 11:27:13', '0000-00-00 00:00:00', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `wishlist`
--

CREATE TABLE `wishlist` (
  `wishlist_id` varchar(8) NOT NULL,
  `uid` varchar(8) NOT NULL,
  `product_id` varchar(8) NOT NULL,
  `w_added_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `activity_logs`
--
ALTER TABLE `activity_logs`
  ADD PRIMARY KEY (`log_id`);

--
-- Indexes for table `cart`
--
ALTER TABLE `cart`
  ADD PRIMARY KEY (`cart_id`);

--
-- Indexes for table `cart_item`
--
ALTER TABLE `cart_item`
  ADD PRIMARY KEY (`cart_item_id`),
  ADD KEY `cart_id` (`cart_id`),
  ADD KEY `product_id` (`product_id`);

--
-- Indexes for table `categories`
--
ALTER TABLE `categories`
  ADD PRIMARY KEY (`cid`);

--
-- Indexes for table `orders`
--
ALTER TABLE `orders`
  ADD PRIMARY KEY (`order_id`),
  ADD KEY `uid` (`uid`);

--
-- Indexes for table `order_items`
--
ALTER TABLE `order_items`
  ADD PRIMARY KEY (`order_item_id`),
  ADD KEY `order_id` (`order_id`),
  ADD KEY `product_id` (`product_id`);

--
-- Indexes for table `payments`
--
ALTER TABLE `payments`
  ADD PRIMARY KEY (`payment_id`),
  ADD KEY `order_id` (`order_id`);

--
-- Indexes for table `products`
--
ALTER TABLE `products`
  ADD PRIMARY KEY (`product_id`);

--
-- Indexes for table `promotions`
--
ALTER TABLE `promotions`
  ADD PRIMARY KEY (`promo_id`);

--
-- Indexes for table `promotion_products`
--
ALTER TABLE `promotion_products`
  ADD PRIMARY KEY (`promo_id`,`product_id`),
  ADD KEY `promo_id` (`promo_id`),
  ADD KEY `product_id` (`product_id`);

--
-- Indexes for table `refunds`
--
ALTER TABLE `refunds`
  ADD PRIMARY KEY (`refund_id`);

--
-- Indexes for table `returns`
--
ALTER TABLE `returns`
  ADD PRIMARY KEY (`return_id`);

--
-- Indexes for table `reviews`
--
ALTER TABLE `reviews`
  ADD PRIMARY KEY (`reviews_id`),
  ADD KEY `uid` (`uid`),
  ADD KEY `product_id` (`product_id`);

--
-- Indexes for table `shipping`
--
ALTER TABLE `shipping`
  ADD PRIMARY KEY (`shipping_id`),
  ADD KEY `order_id` (`order_id`);

--
-- Indexes for table `spec_history`
--
ALTER TABLE `spec_history`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`uid`);

--
-- Indexes for table `wishlist`
--
ALTER TABLE `wishlist`
  ADD PRIMARY KEY (`wishlist_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `orders`
--
ALTER TABLE `orders`
  MODIFY `order_id` int(15) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=30;

--
-- AUTO_INCREMENT for table `order_items`
--
ALTER TABLE `order_items`
  MODIFY `order_item_id` int(255) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=31;

--
-- AUTO_INCREMENT for table `spec_history`
--
ALTER TABLE `spec_history`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
