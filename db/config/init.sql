SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

CREATE SCHEMA IF NOT EXISTS `itpa` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;

CREATE SCHEMA IF NOT EXISTS `fl511` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;
USE `fl511` ;

CREATE TABLE IF NOT EXISTS `cameras` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `coordinate` geometry DEFAULT NULL,
  `camera_id` varchar(100) NOT NULL,
  `last_updated` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `camera_id` (`camera_id`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `congestions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `coordinate` geometry DEFAULT NULL,
  `congestion_id` varchar(100) NOT NULL,
  `last_updated` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `congestion_id` (`congestion_id`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE SCHEMA IF NOT EXISTS `fl511_message_boards` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;
USE `fl511_message_boards` ;

CREATE TABLE IF NOT EXISTS `fl511_message_boards` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `location` varchar(45) DEFAULT NULL,
  `region` varchar(45) DEFAULT NULL,
  `highway` varchar(45) DEFAULT NULL,
  `coordinate` geometry DEFAULT NULL,
  `last_message` varchar(1000) DEFAULT '',
  `last_message_on` datetime DEFAULT NULL,
  `board_id` varchar(100) NOT NULL,
  `last_updated` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `board_id` (`board_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `fl511_message_board_current` (
  `id` int(11) NOT NULL,
  `location` varchar(45) DEFAULT NULL,
  `region` varchar(45) DEFAULT NULL,
  `highway` varchar(45) DEFAULT NULL,
  `coordinate` geometry DEFAULT NULL,
  `last_message` varchar(1000) DEFAULT '',
  `last_message_on` datetime DEFAULT NULL,
  `board_id` varchar(100) NOT NULL,
  `last_updated` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `board_id` (`board_id`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `fl511_message_board_archive` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `board_id` int(11) DEFAULT NULL,
  `message` varchar(1000) DEFAULT '',
  `message_on` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `message_on` (`message_on`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE SCHEMA IF NOT EXISTS `flhsmv_incidents` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;
USE `flhsmv_incidents` ;

CREATE TABLE IF NOT EXISTS `flhsmv_incidents_archive` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `external_id` varchar(45) NOT NULL,
  `type` varchar(50) NOT NULL,
  `date` datetime DEFAULT NULL,
  `coordinate` point NOT NULL,
  `location` varchar(128) DEFAULT NULL,
  `county` varchar(50) DEFAULT NULL,
  `remarks` TEXT DEFAULT NULL,
  `last_updated` datetime DEFAULT NULL,
  `first_updated` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `external_id` (`external_id`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `flhsmv_incidents_current` (
  `id` int(11) unsigned NOT NULL,
  `external_id` varchar(45) NOT NULL,
  `type` varchar(50) NOT NULL,
  `date` datetime DEFAULT NULL,
  `coordinate` point NOT NULL,
  `location` varchar(128) DEFAULT NULL,
  `county` varchar(50) DEFAULT NULL,
  `remarks` TEXT DEFAULT NULL,
  `last_updated` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `external_id` (`external_id`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE SCHEMA IF NOT EXISTS `itpa_parking` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;
USE `itpa_parking` ;

DROP TABLE IF EXISTS `parking_site_types`;

CREATE TABLE IF NOT EXISTS `parking_site_types` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `identifier` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT INTO `parking_site_types` (`id`, `identifier`) 
VALUES (1, "parking garage"), (2, "parking lot"), (3, "on street parking"), (4, "unknown");

DROP TABLE IF EXISTS `parking_sites`;

CREATE TABLE IF NOT EXISTS `parking_sites` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `type_id` int(11) NOT NULL,
  `identifier` varchar(45) NOT NULL,
  `polygon` geometry DEFAULT NULL,
  `number_of_levels` int(11) DEFAULT NULL,
  `centroid` point DEFAULT NULL,
  `capacity` int(11) NOT NULL DEFAULT 0,
  `is_active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `identifier` (`identifier`)
) ENGINE=InnoDB AUTO_INCREMENT=60 DEFAULT CHARSET=utf8;

INSERT INTO `parking_sites`
(`id`,
`type_id`,
`identifier`,
`polygon`,
`number_of_levels`,
`centroid`,
`capacity`,
`is_active`)
VALUES
(1,2,'107 Ave Entrance',GeomFromText("null"),1,GeomFromText("null"),262,1),
(2,2,'3-West of AC-2',GeomFromText("POLYGON((-80.1433002949 25.9098604201,-80.1428067684 25.9101016799,-80.1427263021 25.9099858753,-80.1417553425 25.9097832169,-80.1429569721 25.9092234919,-80.1433002949 25.9098604201))"),1,GeomFromText("POINT(-80.14270929441406 25.909667357103686)"),213,1),
(3,2,'4-West of AC-2',GeomFromText("POLYGON((-80.1427638531 25.909204191,-80.141428113 25.9097204892,-80.1411223412 25.9096336355,-80.1405590773 25.9083452974,-80.1420986652 25.9077807403,-80.1427638531 25.909204191))"),1,GeomFromText("POINT(-80.1416685973163 25.908789165880037)"),765,1),
(4,2,'Apartments',GeomFromText("POLYGON((-80.3704994917 25.7587640653,-80.3707194328 25.758773728,-80.3707194328 25.7583195788,-80.370644331 25.7580925036,-80.3706014156 25.7579523931,-80.3707301617 25.7579330675,-80.3706872463 25.7575610492,-80.3702741861 25.7575658806,-80.3702688217 25.7578895849,-80.3699040413 25.7581359861,-80.3701347113 25.7585080026,-80.3705585003 25.7583630613,-80.3704994917 25.7587640653))"),1,GeomFromText("POINT(-80.37029668826794 25.75816847823505)"),381,1),
(5,2,'Arena Loading Area',GeomFromText("POLYGON((-80.37863 25.758,-80.37786 25.75846,-80.37751 25.75854,-80.37759 25.75761,-80.37818 25.75763,-80.37863 25.758))"),1,GeomFromText("POINT(-80.37798194036439 25.757981326600373)"),21,0),
(6,2,'Between Lot 32 & 33 ',GeomFromText("POLYGON((-80.3711003065 25.7570440868,-80.3718996048 25.757024761,-80.3719210625 25.7573484668,-80.3717333078 25.7573629611,-80.3717333078 25.7573098154,-80.3710788488 25.7573098154,-80.3711003065 25.7570440868))"),1,GeomFromText("POINT(-80.37149601623665 25.757220463180815)"),80,1),
(7,2,'Bookstore/GC',GeomFromText("POLYGON((-80.3718298674 25.7553385778,-80.3718352318 25.7554497024,-80.3714221716 25.7559328514,-80.3708052635 25.7561454364,-80.3702580929 25.7559231885,-80.3700649738 25.7557299291,-80.3699630499 25.7554593654,-80.3699737787 25.7552419477,-80.3702688217 25.7546138499,-80.3704726696 25.7545268823,-80.3707355261 25.7545268823,-80.3718298674 25.7553385778))"),1,GeomFromText("POINT(-80.37060050115541 25.755198409214884)"),340,1),
(10,2,'Cover Area',GeomFromText("null"),1,GeomFromText("null"),138,1),
(11,2,'CSC Compound',GeomFromText("null"),1,GeomFromText("null"),78,1),
(12,2,'CSC Staff Lot',GeomFromText("null"),1,GeomFromText("null"),184,1),
(13,2,'E & W side FIU Stad.',GeomFromText("null"),1,GeomFromText("null"),19,1),
(14,2,'E. Aquatic Cntr',GeomFromText("null"),1,GeomFromText("null"),0,1),
(15,2,'E. of Central Rec.',GeomFromText("POLYGON((-80.1432305574 25.912586627,-80.1427692175 25.9127217294,-80.1426780224 25.9123936233,-80.1431339979 25.9122971213,-80.1432305574 25.912586627))"),1,GeomFromText("POINT(-80.14292387113528 25.912465944853096)"),62,1),
(16,2,'East of  W-5 & W-6',GeomFromText("null"),1,GeomFromText("null"),83,1),
(17,2,'East of Building',GeomFromText("null"),1,GeomFromText("null"),175,1),
(18,2,'East of lot 2',GeomFromText("null"),1,GeomFromText("null"),199,1),
(19,2,'East of OU',GeomFromText("null"),1,GeomFromText("null"),10,1),
(20,2,'East of PAC',GeomFromText("POLYGON((-80.3719854355 25.7531933704,-80.3720390797 25.7531112333,-80.3720068932 25.752434808,-80.3691208363 25.7525845882,-80.3691798449 25.7529904433,-80.3692817688 25.7530097697,-80.3693944216 25.7530532541,-80.3707462549 25.7529904433,-80.3707623482 25.7530580857,-80.3712397814 25.7531402229,-80.3715187311 25.7531015701,-80.3717386723 25.7531402229,-80.3719854355 25.7531933704))"),1,GeomFromText("POINT(-80.37118967265997 25.752743921660283)"),535,1),
(21,2,'East of PG-2',GeomFromText("POLYGON((-80.3716742992 25.7533238233,-80.3716742992 25.7534591076,-80.3714811802 25.753604055,-80.3711700439 25.7542031688,-80.3705263138 25.7541451902,-80.3704082966 25.7539809173,-80.3709447384 25.7534591076,-80.3713846207 25.7532755074,-80.3716742992 25.7533238233))"),1,GeomFromText("POINT(-80.3708958085 25.753939665477887)"),202,1),
(22,2,'East of W-10',GeomFromText("null"),1,GeomFromText("null"),62,1),
(23,2,'East of W-2',GeomFromText("POLYGON((-80.3814375401 25.7532271915,-80.3814697266 25.7535267498,-80.3812122345 25.7535557392,-80.3810191154 25.7532851706,-80.3809225559 25.7532658442,-80.3807401657 25.7533238233,-80.3798389435 25.7529372957,-80.379152298 25.7529372957,-80.379152298 25.7525797566,-80.381244421 25.7525990831,-80.381244421 25.7529276325,-80.3809332848 25.7530049381,-80.3814375401 25.7532271915))"),1,GeomFromText("POINT(-80.38043792934332 25.752801900969246)"),378,1),
(24,2,'GC Space-by-Space',GeomFromText("POLYGON((-80.3718298674 25.7569619523,-80.3712880611 25.7569716152,-80.3712773323 25.7565561108,-80.3718405962 25.7565657737,-80.3718298674 25.7569619523))"),1,GeomFromText("POINT(-80.37155896425 25.756763863000003)"),69,1),
(25,2,'Greek Housing',GeomFromText("null"),1,GeomFromText("null"),7,1),
(26,2,'Housing Lot',GeomFromText("POLYGON((-80.1418840885 25.9127699802,-80.1416105032 25.9132524874,-80.1407200098 25.9139424692,-80.1410257816 25.9131752864,-80.1413422823 25.9133152132,-80.141428113 25.9131608112,-80.1410847902 25.9129967588,-80.1413208246 25.9125190757,-80.1418840885 25.9127699802))"),1,GeomFromText("POINT(-80.14146474943118 25.912900202517406)"),0,1),
(27,2,'Loading Area AC-2',GeomFromText("null"),1,GeomFromText("null"),1,1),
(28,2,'Loading Area GC',GeomFromText("null"),1,GeomFromText("null"),3,1),
(29,2,'Loading Area PAC',GeomFromText("null"),1,GeomFromText("null"),4,1),
(30,2,'Loading Area PC',GeomFromText("null"),1,GeomFromText("null"),13,1),
(31,2,'North of OE',GeomFromText("null"),1,GeomFromText("null"),9,1),
(32,2,'North of W-7',GeomFromText("null"),1,GeomFromText("null"),2,1),
(33,2,'North Univ Towers',GeomFromText("POLYGON((-80.3766202927 25.7553434093,-80.3761696815 25.7553917244,-80.3757512569 25.7553144203,-80.3757727146 25.7549955405,-80.3759121895 25.7549472253,-80.3765773773 25.7549568884,-80.3766524792 25.7550535187,-80.3766202927 25.7553434093))"),1,GeomFromText("POINT(-80.37620799881428 25.755143246699998)"),95,1),
(34,2,'PARKVIEW PARK. GARAGE',GeomFromText("POLYGON((-80.3773766756 25.7548650894,-80.3771674633 25.7548602579,-80.3771567345 25.753918107,-80.3773981333 25.7539567595,-80.3773766756 25.7548650894))"),1,GeomFromText("POINT(-80.377274751675 25.75440005345)"),292,1),
(35,1,'PG-1 GOLD',GeomFromText("POLYGON((-80.3725165129 25.7551791381,-80.3716474771 25.7551646435,-80.3716206551 25.7551259914,-80.3716099262 25.7545848607,-80.3716957569 25.7545172192,-80.372505784 25.7545123877,-80.3725326061 25.7545558715,-80.3725165129 25.7551791381))"),5,GeomFromText("POINT(-80.37206961885235 25.754698099079377)"),1002,1),
(36,1,'PG-2 BLUE',GeomFromText("POLYGON((-80.3725272417 25.7541451902,-80.3724628687 25.7542031688,-80.3716742992 25.7541935057,-80.3716367483 25.7541403586,-80.3716260195 25.7535847287,-80.3717011213 25.7535460761,-80.3724682331 25.7535460761,-80.3725326061 25.7535895603,-80.3725272417 25.7541451902))"),5,GeomFromText("POINT(-80.37207035169558 25.753739284108903)"),1002,1),
(37,1,'PG-3 PANTHER',GeomFromText("POLYGON((-80.3803217411 25.758097335,-80.3803217411 25.7587833907,-80.3793668747 25.7587833907,-80.3793668747 25.758097335,-80.3803217411 25.758097335))"),6,GeomFromText("POINT(-80.3798443079 25.75844036285)"),1441,1),
(38,1,'PG-4 RED',GeomFromText("POLYGON((-80.3736591339 25.7604888502,-80.3726345301 25.760503344,-80.3726291656 25.7598172982,-80.3736644983 25.7598172982,-80.3736591339 25.7604888502))"),6,GeomFromText("POINT(-80.373146831975 25.760156697650004)"),1438,1),
(39,1,'PG-5 MARKET STATION',GeomFromText("POLYGON((-80.3721570969 25.7605709822,-80.3710520267 25.7605613196,-80.3710520267 25.7597303344,-80.3721785545 25.759768985,-80.3721570969 25.7605709822))"),7,GeomFromText("POINT(-80.37156609640077 25.760145772810404)"),1950,1),
(40,1,'PG-6 TECH STATION',GeomFromText("POLYGON((-80.375225544 25.7603197547,-80.3744637966 25.7605419944,-80.3737342358 25.7605130066,-80.3737664223 25.7597786477,-80.374506712 25.759768985,-80.3749787807 25.7595853945,-80.375225544 25.7603197547))"),7,GeomFromText("POINT(-80.37449506864503 25.760107122331206)"),1950,1),
(41,2,'President House',GeomFromText("null"),1,GeomFromText("null"),56,1),
(42,2,'Pub. Safety',GeomFromText("null"),1,GeomFromText("null"),19,1),
(43,2,'Royal Caribbean',GeomFromText("null"),1,GeomFromText("null"),28,1),
(44,2,'So. Phys. Plant',GeomFromText("null"),1,GeomFromText("null"),0,1),
(45,2,'South Koven',GeomFromText("null"),1,GeomFromText("null"),0,1),
(46,2,'South of AHC1',GeomFromText("null"),1,GeomFromText("null"),8,1),
(47,2,'South of PG-3',GeomFromText("POLYGON((-80.3817272186 25.7565995939,-80.3817486763 25.7571310526,-80.3814804554 25.7572759954,-80.3812658787 25.7575755434,-80.381115675 25.7577977883,-80.3802573681 25.7578267767,-80.3802466393 25.7576238576,-80.3807294369 25.7575368921,-80.3812122345 25.7566962229,-80.3817272186 25.7565995939))"),1,GeomFromText("POINT(-80.38138354882211 25.75705380892481)"),221,1),
(48,2,'South of REC',GeomFromText("POLYGON((-80.3783476353 25.7554690284,-80.3779399395 25.7557879069,-80.3776931763 25.755749255,-80.3773713112 25.7558265588,-80.3770601749 25.7558941996,-80.3768134117 25.7556043103,-80.3774678707 25.7552467792,-80.3778862953 25.7552564422,-80.3783476353 25.7554690284))"),1,GeomFromText("POINT(-80.3775724768625 25.75560431005)"),194,1),
(49,2,'South of W-9',GeomFromText("null"),1,GeomFromText("null"),41,1),
(50,2,'Student Housing',GeomFromText("POLYGON((-80.3766900301 25.7530919069,-80.3764486313 25.7530339277,-80.3737664223 25.7530580857,-80.3735303879 25.7531112333,-80.3734070063 25.7531547176,-80.3734284639 25.7528454952,-80.3739005327 25.7528599901,-80.373916626 25.7526570625,-80.3766953945 25.7526087463,-80.3766900301 25.7530919069))"),1,GeomFromText("POINT(-80.37524517269048 25.75284055382616)"),386,1),
(51,2,'Tower',GeomFromText("null"),1,GeomFromText("null"),27,1),
(52,2,'W-2 Compound',GeomFromText("null"),1,GeomFromText("null"),37,1),
(53,2,'W. of Library',GeomFromText("POLYGON((-80.141953826 25.9116457308,-80.1411706209 25.9115251026,-80.1410901546 25.9115299277,-80.140414238 25.9118049599,-80.1401245594 25.9112162937,-80.1401352882 25.9109026589,-80.1402908564 25.9106951769,-80.1405698061 25.9105890232,-80.1408004761 25.9105697225,-80.1412135363 25.9106421,-80.1421952248 25.9108351066,-80.141953826 25.9116457308))"),1,GeomFromText("POINT(-80.14111069784121 25.91113421137821)"),245,1),
(54,2,'West of AC-1',GeomFromText("POLYGON((-80.1423829794 25.9106614007,-80.1405966282 25.9103188133,-80.1405322552 25.9101209807,-80.1411491632 25.9097108388,-80.1426780224 25.9100244768,-80.1427799463 25.9101595822,-80.1423829794 25.9106614007))"),1,GeomFromText("POINT(-80.14163641080812 25.910169177724313)"),422,1),
(55,2,'West of ESC',GeomFromText("null"),1,GeomFromText("null"),22,1),
(56,2,'West of Green Lib',GeomFromText("null"),1,GeomFromText("null"),17,1),
(57,2,'West of Koven',GeomFromText("POLYGON((-80.140709281 25.9074236686,-80.140017271 25.9076552828,-80.1394969225 25.9065020327,-80.1401942968 25.9062607655,-80.140709281 25.9074236686))"),1,GeomFromText("POINT(-80.140104442825 25.906960437400002)"),230,1),
(58,2,'West of OU',GeomFromText("null"),1,GeomFromText("null"),39,1),
(59,2,'Parking lot 9',GeomFromText("POLYGON((-80.37863 25.758,-80.37894 25.75845,-80.37882 25.75897,-80.37844 25.75926,-80.37791 25.75936,-80.3772 25.75922,-80.3772 25.75863,-80.37751 25.75853,-80.37759 25.75762,-80.37819 25.75763,-80.37863 25.758))"),1,GeomFromText("POINT(-80.3780798738504 25.758525722639646)"),589,1);

CREATE SCHEMA IF NOT EXISTS `itpa_transit` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;
USE `itpa_transit` ;

DROP TABLE IF EXISTS `utma_buses`;

CREATE TABLE IF NOT EXISTS `utma_buses` (
  `id` varchar(20) NOT NULL,
  `name` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT INTO `utma_buses`
(`id`,
`name`)
VALUES
('5012', 'MPV-1'),
('0', 'MPV-2'),
('5011', 'MPV-3'),
('5667', 'SW-1'),
('7140', 'SW-2'),
('8828', 'SW-3'),
('1103', 'SW-4'),
('4056', 'SW-5'),
('4061', 'SW-6'),
('25001', 'SW-7');

CREATE TABLE IF NOT EXISTS `current_buses` (
  `fleet` varchar(20) NOT NULL,
  `id` varchar(20) NOT NULL,
  `name` varchar(20) NOT NULL,
  `route_id` varchar(20) DEFAULT NULL,
  `direction` varchar(45) DEFAULT NULL,
  `trip_id` varchar(20) DEFAULT NULL,
  `coordinate` point NOT NULL,
  `coordinate_updated` datetime NOT NULL,
  `occupancy_percentage` double DEFAULT NULL,
  `speed_mph` double DEFAULT NULL,
  `heading_degree` int(3) DEFAULT NULL,
  `last_updated` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`fleet`, `id`),
  KEY `last_updated` (`last_updated`),
  KEY `coordinate_updated` (`coordinate_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `archive_buses` (
  `pkey` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `fleet` varchar(20) NOT NULL,
  `id` varchar(20) NOT NULL,
  `name` varchar(20) NOT NULL,
  `route_id` varchar(20) DEFAULT NULL,
  `direction` varchar(45) DEFAULT NULL,
  `trip_id` varchar(20) DEFAULT NULL,
  `coordinate` point NOT NULL,
  `coordinate_updated` datetime NOT NULL,
  `occupancy_percentage` double DEFAULT NULL,
  `speed_mph` double DEFAULT NULL,
  `heading_degree` int(3) DEFAULT NULL,
  PRIMARY KEY (`pkey`),
  KEY `fleet_id` (`fleet`, `id`),
  KEY `coordinate_updated` (`coordinate_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `bus_stops` (
  `fleet` varchar(20) NOT NULL,
  `id` varchar(20) NOT NULL,
  `code` varchar(20) DEFAULT '',
  `name` varchar(100) DEFAULT '',
  `desc` varchar(1000) DEFAULT '',
  `coordinate` point DEFAULT NULL,
  `last_updated` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`fleet`, `id`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `bus_routes` (
  `fleet` varchar(20) NOT NULL,
  `id` varchar(20) NOT NULL,
  `name` varchar(100) DEFAULT '',
  `color` varchar(20) DEFAULT 'FF8000',
  `compressed_multi_linestring` text NOT NULL,
  `ndirections` int(11) NOT NULL,
  `direction_names` text NOT NULL,
  `direction_shapes` text NOT NULL,
  `compressed_stop_ids` text NOT NULL,
  `last_updated` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`fleet`, `id`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `bus_etas` (
  `fleet` varchar(20) NOT NULL,
  `route_id` varchar(20) NOT NULL,
  `bus_id` varchar(20) NOT NULL,
  `stop_id` varchar(20) NOT NULL,
  `eta` datetime NOT NULL,
  `last_updated` datetime DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `pkey` (`fleet`,`bus_id`,`stop_id`),
  KEY `eta` (`eta`),
  KEY `last_updated` (`last_updated`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE SCHEMA IF NOT EXISTS `itpa_messaging` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `itpa_messaging` ;

CREATE TABLE IF NOT EXISTS `itpa_notifications` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(100) NOT NULL,
  `summary` varchar(1024) NOT NULL,
  `icon` text DEFAULT NULL,
  `url` text DEFAULT NULL,
  `start_on` datetime DEFAULT NULL,
  `expire_on` datetime DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  INDEX(is_active),
  INDEX(start_on),
  INDEX(expire_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE SCHEMA IF NOT EXISTS `itpa_app` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `itpa_app`;

CREATE TABLE IF NOT EXISTS `archive_device_tracking` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `uuid` varchar(45) NOT NULL,
  `coordinate` geometry NOT NULL,
  `coordinate_on` datetime NOT NULL,
  `is_stationary` tinyint(1) DEFAULT '0',
  `altitude` double DEFAULT '0',
  `speed_mph` double DEFAULT '0',
  `heading_degree` int(3) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `uuid` (`uuid`),
  KEY `coordinate_on` (`coordinate_on`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `current_device_tracking` (
  `uuid` varchar(45) NOT NULL,
  `coordinate` geometry NOT NULL,
  `coordinate_on` datetime NOT NULL,
  `is_stationary` tinyint(1) DEFAULT '0',
  `altitude` double DEFAULT '0',
  `speed_mph` double DEFAULT '0',
  `heading_degree` int(3) DEFAULT '0',
  PRIMARY KEY (`uuid`),
  KEY `coordinate_on` (`coordinate_on`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE SCHEMA IF NOT EXISTS `itpa_video` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;
USE `itpa_video` ;

CREATE TABLE IF NOT EXISTS `bus_videos` (
  `uuid` VARCHAR(60) NOT NULL,
  `fleet` varchar(20) NOT NULL,
  `bus_id` varchar(20) NOT NULL,
  `bus_name` varchar(20) NOT NULL,
  `camera_type` varchar(20) NOT NULL,
  `has_frame_images` TINYINT(1) DEFAULT '1',
  `created_on` datetime NOT NULL,
  `recording_ended` datetime DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  KEY `fleet_bus_id` (`fleet`, `bus_id`),
  KEY `created_on` (`created_on`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;

