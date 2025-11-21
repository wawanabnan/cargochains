-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Nov 16, 2025 at 04:28 AM
-- Server version: 8.0.30
-- PHP Version: 8.1.10

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `cargochains`
--

-- --------------------------------------------------------

--
-- Table structure for table `locations`
--

CREATE TABLE `locations` (
  `id` bigint NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `code` varchar(20) NOT NULL,
  `name` varchar(150) NOT NULL,
  `kind` varchar(20) NOT NULL,
  `lft` int DEFAULT NULL,
  `rght` int DEFAULT NULL,
  `iata_code` varchar(10) DEFAULT NULL,
  `unlocode` varchar(10) DEFAULT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `parent_id` bigint DEFAULT NULL,
  `iso_code` varchar(20) DEFAULT NULL,
  `note` longtext,
  `postal_code` varchar(10) DEFAULT NULL,
  `source` varchar(100) DEFAULT NULL,
  `status` varchar(8) NOT NULL,
  `timezone` varchar(50) DEFAULT NULL,
  `altitude` decimal(8,2) DEFAULT NULL,
  `country_code` varchar(2) DEFAULT NULL,
  `display_name` varchar(255) DEFAULT NULL
) ;

--
-- Dumping data for table `locations`
--

INSERT INTO `locations` (`id`, `created_at`, `updated_at`, `code`, `name`, `kind`, `lft`, `rght`, `iata_code`, `unlocode`, `latitude`, `longitude`, `parent_id`, `iso_code`, `note`, `postal_code`, `source`, `status`, `timezone`, `altitude`, `country_code`, `display_name`) VALUES
(1, '2025-09-18 09:56:46.808886', '2025-09-18 09:56:46.808930', 'LOC1', 'Indonesia', 'country', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(2, '2025-09-18 09:56:46.828197', '2025-09-18 09:56:46.828236', 'LOC2', 'Jakarta', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(3, '2025-09-18 09:56:46.831871', '2025-09-18 09:56:46.831901', 'LOC3', 'Surabaya', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(4, '2025-09-18 09:56:46.834618', '2025-09-18 09:56:46.834647', 'LOC4', 'Bandung', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(5, '2025-09-18 09:56:46.837260', '2025-09-18 09:56:46.837289', 'LOC5', 'Medan', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(6, '2025-09-18 09:56:46.840009', '2025-09-18 09:56:46.840036', 'LOC6', 'Semarang', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(7, '2025-09-18 09:56:46.842661', '2025-09-18 09:56:46.842690', 'LOC7', 'Makassar', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(8, '2025-09-18 09:56:46.845969', '2025-09-18 09:56:46.846002', 'LOC8', 'Palembang', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(9, '2025-09-18 09:56:46.848886', '2025-09-18 09:56:46.848934', 'LOC9', 'Tangerang', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(10, '2025-09-18 09:56:46.852799', '2025-09-18 09:56:46.852830', 'LOC10', 'Depok', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(11, '2025-09-18 09:56:46.855706', '2025-09-18 09:56:46.855737', 'LOC11', 'Bekasi', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(12, '2025-09-18 09:56:46.858413', '2025-09-18 09:56:46.858442', 'LOC12', 'Bogor', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(13, '2025-09-18 09:56:46.861331', '2025-09-18 09:56:46.861361', 'LOC13', 'Malang', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(14, '2025-09-18 09:56:46.863930', '2025-09-18 09:56:46.863958', 'LOC14', 'Yogyakarta', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(15, '2025-09-18 09:56:46.866618', '2025-09-18 09:56:46.866647', 'LOC15', 'Denpasar', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(16, '2025-09-18 09:56:46.869310', '2025-09-18 09:56:46.869339', 'LOC16', 'Balikpapan', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(17, '2025-09-18 09:56:46.872550', '2025-09-18 09:56:46.872593', 'LOC17', 'Samarinda', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(18, '2025-09-18 09:56:46.875340', '2025-09-18 09:56:46.875371', 'LOC18', 'Pontianak', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(19, '2025-09-18 09:56:46.878007', '2025-09-18 09:56:46.878036', 'LOC19', 'Banjarmasin', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(20, '2025-09-18 09:56:46.880746', '2025-09-18 09:56:46.880776', 'LOC20', 'Pekanbaru', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(21, '2025-09-18 09:56:46.883391', '2025-09-18 09:56:46.883419', 'LOC21', 'Batam', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(22, '2025-09-18 09:56:46.886001', '2025-09-18 09:56:46.886031', 'LOC22', 'Padang', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(23, '2025-09-18 09:56:46.889196', '2025-09-18 09:56:46.889226', 'LOC23', 'Banda Aceh', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(24, '2025-09-18 09:56:46.893036', '2025-09-18 09:56:46.893083', 'LOC24', 'Manado', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(25, '2025-09-18 09:56:46.897298', '2025-09-18 09:56:46.897342', 'LOC25', 'Ambon', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(26, '2025-09-18 09:56:46.900407', '2025-09-18 09:56:46.900450', 'LOC26', 'Jayapura', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(27, '2025-09-18 09:56:46.903401', '2025-09-18 09:56:46.903441', 'LOC27', 'Kupang', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(28, '2025-09-18 09:56:46.906340', '2025-09-18 09:56:46.906386', 'LOC28', 'Mataram', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(29, '2025-09-18 09:56:46.909502', '2025-09-18 09:56:46.909542', 'LOC29', 'Palu', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(30, '2025-09-18 09:56:46.912493', '2025-09-18 09:56:46.912532', 'LOC30', 'Kendari', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(31, '2025-09-18 09:56:46.915579', '2025-09-18 09:56:46.915618', 'LOC31', 'Cirebon', 'city', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(32, '2025-09-18 09:56:46.918526', '2025-09-18 09:56:46.918568', 'LOC32', 'Tanjung Priok', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(33, '2025-09-18 09:56:46.921579', '2025-09-18 09:56:46.921623', 'LOC33', 'Tanjung Perak', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(34, '2025-09-18 09:56:46.924659', '2025-09-18 09:56:46.924701', 'LOC34', 'Belawan', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(35, '2025-09-18 09:56:46.927729', '2025-09-18 09:56:46.927771', 'LOC35', 'Tanjung Emas', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(36, '2025-09-18 09:56:46.930286', '2025-09-18 09:56:46.930313', 'LOC36', 'Soekarno-Hatta (Makassar)', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(37, '2025-09-18 09:56:46.932750', '2025-09-18 09:56:46.932777', 'LOC37', 'Teluk Bayur', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 22, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(38, '2025-09-18 09:56:46.935203', '2025-09-18 09:56:46.935231', 'LOC38', 'Batu Ampar', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 21, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(39, '2025-09-18 09:56:46.937811', '2025-09-18 09:56:46.937856', 'LOC39', 'Dwikora', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(40, '2025-09-18 09:56:46.942560', '2025-09-18 09:56:46.942601', 'LOC40', 'Trisakti', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 19, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(41, '2025-09-18 09:56:46.946027', '2025-09-18 09:56:46.946071', 'LOC41', 'Boom Baru', 'port', NULL, NULL, NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(42, '2025-09-18 09:56:46.950346', '2025-09-18 09:56:46.950385', 'LOC42', 'Soekarno–Hatta', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(43, '2025-09-18 09:56:46.953856', '2025-09-18 09:56:46.953896', 'LOC43', 'Juanda', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(44, '2025-09-18 09:56:46.957982', '2025-09-18 09:56:46.958040', 'LOC44', 'Kualanamu', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(45, '2025-09-18 09:56:46.961803', '2025-09-18 09:56:46.961851', 'LOC45', 'Ahmad Yani', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(46, '2025-09-18 09:56:46.965472', '2025-09-18 09:56:46.965515', 'LOC46', 'Sultan Hasanuddin', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(47, '2025-09-18 09:56:46.969167', '2025-09-18 09:56:46.969211', 'LOC47', 'Ngurah Rai', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(48, '2025-09-18 09:56:46.973232', '2025-09-18 09:56:46.973277', 'LOC48', 'Minangkabau', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 22, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(49, '2025-09-18 09:56:46.977426', '2025-09-18 09:56:46.977469', 'LOC49', 'Sultan Syarif Kasim II', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 20, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(50, '2025-09-18 09:56:46.980246', '2025-09-18 09:56:46.980273', 'LOC50', 'Sam Ratulangi', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 24, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(51, '2025-09-18 09:56:46.982966', '2025-09-18 09:56:46.982997', 'LOC51', 'Supadio', 'airport', NULL, NULL, NULL, NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(52, '2025-09-18 09:56:46.986075', '2025-09-18 09:56:46.986105', 'LOC52', 'Pluit Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(53, '2025-09-18 09:56:46.989328', '2025-09-18 09:56:46.989369', 'LOC53', 'Marunda Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(54, '2025-09-18 09:56:46.992330', '2025-09-18 09:56:46.992372', 'LOC54', 'Paotere Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(55, '2025-09-18 09:56:46.995353', '2025-09-18 09:56:46.995395', 'LOC55', 'Kariangau Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(56, '2025-09-18 09:56:46.998458', '2025-09-18 09:56:46.998501', 'LOC56', 'Loa Janan Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(57, '2025-09-18 09:56:47.001654', '2025-09-18 09:56:47.001699', 'LOC57', 'Kuin Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 19, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(58, '2025-09-18 09:56:47.004636', '2025-09-18 09:56:47.004666', 'LOC58', 'Sungai Kakap Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(59, '2025-09-18 09:56:47.007249', '2025-09-18 09:56:47.007277', 'LOC59', 'Cirebon Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 31, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(60, '2025-09-18 09:56:47.009855', '2025-09-18 09:56:47.009883', 'LOC60', 'Tanjung Priok Coal Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL),
(61, '2025-09-18 09:56:47.012615', '2025-09-18 09:56:47.012646', 'LOC61', 'Tanjung Perak Bulk Jetty', 'jetty', NULL, NULL, NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL, 'active', NULL, NULL, NULL, NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `locations`
--
ALTER TABLE `locations`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `locations_code_5785065d_uniq` (`code`),
  ADD KEY `loc_kind_idx` (`kind`),
  ADD KEY `loc_parent_idx` (`parent_id`),
  ADD KEY `loc_name_idx` (`name`),
  ADD KEY `loc_iata_idx` (`iata_code`),
  ADD KEY `loc_unlocode_idx` (`unlocode`),
  ADD KEY `loc_code_idx` (`code`),
  ADD KEY `loc_parent_kind_idx` (`parent_id`,`kind`),
  ADD KEY `loc_kind_name_idx` (`kind`,`name`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `locations`
--
ALTER TABLE `locations`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `locations`
--
ALTER TABLE `locations`
  ADD CONSTRAINT `locations_parent_id_be56a103_fk_locations_id` FOREIGN KEY (`parent_id`) REFERENCES `locations` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
