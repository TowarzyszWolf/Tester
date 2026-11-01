BEGIN TRANSACTION;
CREATE TABLE import_receipts (
    token TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL,
    result_id INTEGER REFERENCES results(id) ON DELETE SET NULL
);
CREATE TABLE results (
    id INTEGER PRIMARY KEY,
    edition TEXT NOT NULL DEFAULT '',
    cpu TEXT NOT NULL DEFAULT '',
    gpu TEXT NOT NULL DEFAULT '',
    threads INTEGER CHECK(threads > 0),
    os TEXT NOT NULL DEFAULT '',
    measured_at TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    cores INTEGER CHECK(cores > 0),
    clock_mhz REAL CHECK(clock_mhz > 0),
    benchmark_version TEXT NOT NULL DEFAULT '',
    system_name TEXT NOT NULL DEFAULT '',
    architecture TEXT NOT NULL DEFAULT '',
    source_file TEXT NOT NULL DEFAULT '',
    os_name TEXT NOT NULL DEFAULT '',
    os_version TEXT NOT NULL DEFAULT '',
    os_build TEXT NOT NULL DEFAULT '',
    cpu_single REAL CHECK(cpu_single > 0),
    cpu_single_unit TEXT NOT NULL DEFAULT '',
    cpu_multi REAL CHECK(cpu_multi > 0),
    cpu_multi_unit TEXT NOT NULL DEFAULT '',
    gpu_score REAL CHECK(gpu_score > 0),
    gpu_score_unit TEXT NOT NULL DEFAULT '',
    opengl REAL CHECK(opengl > 0),
    opengl_unit TEXT NOT NULL DEFAULT '',
    shading REAL CHECK(shading > 0),
    shading_unit TEXT NOT NULL DEFAULT '',
    opengl_software REAL CHECK(opengl_software > 0),
    opengl_software_unit TEXT NOT NULL DEFAULT '',
    opengl_hardware REAL CHECK(opengl_hardware > 0),
    opengl_hardware_unit TEXT NOT NULL DEFAULT '',
    opengl_standard REAL CHECK(opengl_standard > 0),
    opengl_standard_unit TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
INSERT INTO "results" VALUES(1,'R11.5','AMD G-T44R Processor','AMD Radeon HD 6250 Graphics',1,'Windows 7, 64 Bit, Home Premium Edition Service Pack 1 (build 7601)','','C4DBUILDID=CB25720demo
OPENGLVENDOR=Advanced_Micro_Devices
OPENGLVERSION=4.5.13399 Compatibility Profile Context 15.200.1062.1004
Pole wyniku: CBCPU1

C4DBUILDID=CB25720demo
OPENGLVENDOR=Advanced_Micro_Devices
OPENGLVERSION=4.5.13399 Compatibility Profile Context 15.200.1062.1004
Pole wyniku: CBCPUX

C4DBUILDID=CB25720demo
OPENGLVENDOR=Advanced_Micro_Devices
OPENGLVERSION=4.5.13399 Compatibility Profile Context 15.200.1062.1004
Pole wyniku: CBOPENGL
CBOPENGLQUALITY=99.290596',1,1200.0,'11.529','Fujitsu Futro S700','64 Bit','11_529_CB25720demo_1C_1T_1200_AMD_G_T44R_Processor_Advanced_Micro_Devices_AMD_Radeon_HD_6250_Graphics_4_5_13399_Compatibility_Profile_Context_15_200_1062_1004_64_Bit.txt','Windows','7','7601',0.222723,'cb',0.222723,'cb',NULL,'',4.36693,'fps',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.378Z');
INSERT INTO "results" VALUES(4,'R11.5','Intel Atom CPU N2100','GDI Generic',2,'64 Bit, Unknown Edition (101) (build 9200)','','C4DBUILDID=CB25720demo
OPENGLVENDOR=Microsoft Corporation
OPENGLVERSION=1.1.0
Pole wyniku: CBCPUX',1,1600.0,'11.529','','32 Bit','11_529_CB25720demo_1C_2T_1600__Intel_Atom_CPU_N2100__Microsoft_Corporation_GDI_Generic_1_1_0_32_Bit.txt','','','9200',NULL,'',0.223569,'cb',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(5,'R15','AMD Athlon(tm) II X2 250 Processor','GeForce GT 730/PCIe/SSE2',2,'Windows 8, 64 Bit, Professional Edition (build 9200)','','C4DBUILDID=RC83328demo
OPENGLVENDOR=NVIDIA Corporation
OPENGLVERSION=4.6.0 NVIDIA 456.71
DRIVERVERSION=456.71
Pole wyniku: CBCPUX',2,3020.0,'15.037','','64 Bit','15_037_RC83328demo_2C_2T_3020_AMD_Athlon_tm__II_X2_250_Processor_NVIDIA_Corporation_GeForce_GT_730_PCIe_SSE2_4_6_0_NVIDIA_456_71_64_Bit.txt','Windows','8','9200',NULL,'',128.585114,'cb',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(6,'R15','Intel Core i7-3770 CPU','GeForce GT 620/PCIe/SSE2',8,'Windows 7, 64 Bit, Professional Edition Service Pack 1 (build 7601)','','C4DBUILDID=RC83328demo
OPENGLVENDOR=NVIDIA Corporation
OPENGLVERSION=3.2.0
DRIVERVERSION=320.49
Pole wyniku: CBCPU1

C4DBUILDID=RC83328demo
OPENGLVENDOR=NVIDIA Corporation
OPENGLVERSION=3.2.0
DRIVERVERSION=320.49
Pole wyniku: CBCPUX

C4DBUILDID=RC83328demo
OPENGLVENDOR=NVIDIA Corporation
OPENGLVERSION=3.2.0
DRIVERVERSION=320.49
Pole wyniku: CBOPENGL
CBOPENGLQUALITY=99.616068',4,3400.0,'15.037','','64 Bit','15_037_RC83328demo_4C_8T_3400__Intel_Core_i7_3770_CPU__NVIDIA_Corporation_GeForce_GT_620_PCIe_SSE2_3_2_0_64_Bit — kopia.txt','Windows','7','7601',138.354208,'cb',661.868123,'cb',NULL,'',19.04443,'fps',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(9,'R15','AMD G-T44R Processor','AMD Radeon HD 6250 Graphics',1,'Windows 7, 64 Bit, Home Premium Edition Service Pack 1 (build 7601)','','C4DBUILDID=RC184115demo
OPENGLVENDOR=Advanced_Micro_Devices
OPENGLVERSION=3.2.13399 Compatibility Profile Context 15.200.1062.1004
DRIVERVERSION=8.14.1.6463
Pole wyniku: CBCPU1

C4DBUILDID=RC184115demo
OPENGLVENDOR=Advanced_Micro_Devices
OPENGLVERSION=3.2.13399 Compatibility Profile Context 15.200.1062.1004
DRIVERVERSION=8.14.1.6463
Pole wyniku: CBCPUX

C4DBUILDID=RC184115demo
OPENGLVENDOR=Advanced_Micro_Devices
OPENGLVERSION=3.2.13399 Compatibility Profile Context 15.200.1062.1004
DRIVERVERSION=8.14.1.6463
Pole wyniku: CBOPENGL
CBOPENGLQUALITY=98.017265',1,1200.0,'15.038','Fujitsu Futro S700','64 Bit','15_038_RC184115demo_1C_1T_1200_AMD_G_T44R_Processor_Advanced_Micro_Devices_AMD_Radeon_HD_6250_Graphics_3_2_13399_Compatibility_Profile_Context_15_200_1062_1004_64_Bit.txt','Windows','7','7601',18.031371,'cb',18.031371,'cb',NULL,'',3.631861,'fps',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(12,'2026','13th Gen Intel Core i5-1334U','Intel(R) Iris(R) Xe Graphics',12,'Windows 11, 64 Bit, Professional Edition (build 26100)','','C4DBUILDID=2026_benchmark_a07ad25f50fc_2228061545
Pole wyniku: CBCPU1
CBCPU1PEAK=417.697903
CBCPU1ARRAY={417.698}

C4DBUILDID=2026_benchmark_a07ad25f50fc_2228061545
Pole wyniku: CBCPUX
CBCPUXPEAK=1510.767420
CBCPUXARRAY={1510.767}',10,2500.0,'2026.100','Dell Pro 15 PV15250','64 Bit','2026_100_10C_12T_2500_13th_Gen_Intel_Core_i5_1334U_64_Bit.txt','Windows','11','26100',417.697903,'pts',1510.76742,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(14,'2026','Intel Core i3-7020U CPU','Intel(R) HD Graphics 620',4,'Windows 10, 64 Bit, Professional Edition (build 19045)','','C4DBUILDID=2026_benchmark_1659ae2c9f3b_2626460137
Pole wyniku: CBCPUX
CBCPUXPEAK=385.863225
CBCPUXARRAY={385.863}',2,2310.0,'2026.103','HP 250 G6','64 Bit','2026_103_2C_4T_2310_Intel_Core_i3_7020U_CPU_64_Bit.txt','Windows','10','19045',NULL,'',385.863225,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(15,'R20','Intel Xeon CPU X5650','',24,'OS X: Version 10.12.6 (Build 16G1815)','','C4DBUILDID=RBBenchmark270378
Pole wyniku: CBCPU1

C4DBUILDID=RBBenchmark270378
Pole wyniku: CBCPUX',12,2660.0,'20.030','','64 BIT','20_030_12C_24T_2660_Intel_Xeon_CPU_X5650_64_BIT.txt','macOS','10.12.6','16G1815',191.293524,'pts',2704.755553,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(17,'R20','Intel Core i5-5300U CPU','',4,'Windows 10, 64 Bit, Professional Edition (build 16299)','','C4DBUILDID=RBBenchmark270378
Pole wyniku: CBCPU1

C4DBUILDID=RBBenchmark270378
Pole wyniku: CBCPUX',2,2300.0,'20.030','','64 Bit','20_030_2C_4T_2300_Intel_Core_i5_5300U_CPU_64_Bit.txt','Windows','10','16299',280.163109,'pts',540.734733,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(19,'R20','13th Gen Intel Core i5-1334U','',12,'Windows 10, 64 Bit, Professional Edition (build 26100)','','C4DBUILDID=RBBenchmark271150
Pole wyniku: CBCPU1

C4DBUILDID=RBBenchmark271150
Pole wyniku: CBCPUX',10,2500.0,'20.040','','64 Bit','20_040_10C_12T_2500_13th_Gen_Intel_Core_i5_1334U_64_Bit.txt','Windows','10','26100',647.80777,'pts',2163.443728,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(21,'R20','Intel Celeron CPU N3060','',2,'Windows 10, 64 Bit, Professional Edition (build 19045)','','C4DBUILDID=RBBenchmark271150
Pole wyniku: CBCPU1

C4DBUILDID=RBBenchmark271150
Pole wyniku: CBCPUX',2,1600.0,'20.040','','64 Bit','20_040_2C_1600_Intel_Celeron_CPU_N3060_64_Bit.txt','Windows','10','19045',49.256796,'pts',72.734447,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(23,'R20','Intel Core i3-7020U CPU','',4,'Windows 10, 64 Bit, Professional Edition (build 19045)','','C4DBUILDID=RBBenchmark271150
Pole wyniku: CBCPU1

C4DBUILDID=RBBenchmark271150
Pole wyniku: CBCPUX',2,2310.0,'20.040','','64 Bit','20_040_2C_4T_2310_Intel_Core_i3_7020U_CPU_64_Bit.txt','Windows','10','19045',227.617307,'pts',567.14006,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(25,'R23','Intel Core i7-4850HQ CPU','',8,'macOS: Version 10.14.6 (Build 18G6032)','','C4DBUILDID=Unknown
Pole wyniku: CBCPU1
CBCPU1PEAK=750.488513
CBCPU1ARRAY={750.489}

C4DBUILDID=Unknown
Pole wyniku: CBCPUX
CBCPUXPEAK=3891.028230
CBCPUXARRAY={3868.117,3896.238,3908.729}',4,2300.0,'23.105','','64 BIT','23_105_4C_8T_2300_Intel_Core_i7_4850HQ_CPU_64_BIT.txt','macOS','10.14.6','18G6032',750.488513,'pts',3891.02823,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(27,'R23','AMD Athlon(tm) II X2 250 Processor','',2,'Windows 10, 64 Bit, Professional Edition (build 19045)','','C4DBUILDID=RBBenchmark330542
Pole wyniku: CBCPUX
CBCPUXPEAK=734.509280
CBCPUXARRAY={734.509}',2,3020.0,'23.200','','64 Bit','23_200_2C_3020_AMD_Athlon_tm__II_X2_250_Processor_64_Bit.txt','Windows','10','19045',NULL,'',734.50928,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(28,'R23','Intel Core i7-3770 CPU','',8,'Windows 10, 64 Bit, Professional Edition (build 19045)','','C4DBUILDID=RBBenchmark330542
Pole wyniku: CBCPUX
CBCPUXPEAK=3671.255383
CBCPUXARRAY={3671.255,3659.356,3676.851}',4,3400.0,'23.200','','64 Bit','23_200_4C_8T_3400_Intel_Core_i7_3770_CPU_64_Bit.txt','Windows','10','19045',NULL,'',3669.154145,'pts',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(29,'R10','AMD Ryzen 5 5600H with Radeon Graphics','NVIDIA GeForce RTX 3050 Laptop GPU/PCIe/SSE2',12,'WINDOWS 64 BIT 6.2.9200','','MHz (z pliku): 3.3 GHz',NULL,3300.0,'R10','Acer Nitro 5','','Acer Nitro 5 AMD Ryzen 5 5600H with Radeon Graphics.txt','Windows','6.2.9200','9200',10737.0,'CB-CPU',57586.0,'CB-CPU',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',13705.0,'CB-GFX','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(32,'R9.5','Intel Core 2 Duo P7350','Nvidia Geforce 9400M 128M',2,'Mac OS X 10.11.6','','MHz (z pliku): 2000',NULL,2000.0,'9.5','Apple MacBook 13 Aluminum Late 2008','','Apple MacBook 13 Aluminum Late 2008 Intel Core 2 Duo P7350.txt','macOS','10.11.6','',336.0,'CB-CPU',622.0,'CB-CPU',NULL,'',NULL,'',433.0,'CB-GFX',1663.0,'CB-GFX',3231.0,'CB-GFX',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(37,'R9.5','Intel Core 2 Duo T8100','Intel GMA X3100',2,'Mac OS X 10.7.5','','MHz (z pliku): 2100',NULL,2100.0,'9.5','Apple MacBook 13 Early 2008','','Apple MacBook 13 Early 2008 Intel Core 2 Duo T8100.txt','macOS','10.7.5','',199.0,'CB-CPU',276.0,'CB-CPU',NULL,'',NULL,'',247.0,'CB-GFX',724.0,'CB-GFX',1252.0,'CB-GFX',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(42,'R9.5','PowerPC G4 (7400)','ATI Rage Pro',1,'Mac OS X 10.4.11','','MHz (z pliku): 400',NULL,400.0,'9.5','Apple Power Mac G4 (AGP graphics)','','Apple Power Mac G4 (AGP graphics) PowerPC G4 Desktop-CR-9.txt','macOS','10.4.11','',45.0,'CB-CPU',NULL,'',NULL,'',NULL,'',54.0,'CB-GFX',149.0,'CB-GFX',94.0,'CB-GFX',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(46,'2003','PowerPC G4 (7400)','ATI Rage 128 Pro',1,'Mac OS X 10.4.11','','MHz (z pliku): 400MHz',NULL,400.0,'2003 v1','Apple Power Mac G4 (AGP graphics)','','Apple Power Mac G4-CR2003.txt','macOS','10.4.11','',42.0,'CB-CPU',NULL,'',NULL,'',NULL,'',55.0,'CB-GFX',142.0,'CB-GFX',80.0,'CB-GFX',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(50,'R9.5','PowerPC G4 (7400)','ATI Rage Pro',1,'Mac OS X 10.4.11','','MHz (z pliku): 450',NULL,450.0,'9.5','Apple PowerMac G4 (AGP Graphics)','','Apple PowerMac G4 (AGP Graphics) PowerPC G4.txt','macOS','10.4.11','',52.0,'CB-CPU',NULL,'',NULL,'',NULL,'',61.0,'CB-GFX',166.0,'CB-GFX',106.0,'CB-GFX',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(54,'R10','PowerPC G4 (7400)','ATi Rage 128 Pro OpenGL Engine',1,'OS X 32 BIT 10.4.11','','MHz (z pliku): 450MHz',NULL,450.0,'R10','Apple PowerMac G4 (AGP Graphics)','','Apple PowerMac G4 (AGP Graphics) PowerPC G4_CB-10.txt','macOS','10.4.11','',307.0,'CB-CPU',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',41.0,'CB-GFX','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(56,'R9.5','PowerPC G3 (750FX)','ATI Mobility Radeon 7500',1,'Mac OS X 10.4.11','','MHz (z pliku): 700',NULL,700.0,'9.5','Apple iBook (Opaque 16 VRAM)','','Apple iBook G3 PowerPC G3.txt','macOS','10.4.11','',73.0,'CB-CPU',NULL,'',NULL,'',NULL,'',78.0,'CB-GFX',177.0,'CB-GFX',124.0,'CB-GFX',NULL,'','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(60,'R10','Intel(R) Celeron(R) CPU N3060 @ 1.60GHz','Intel(R) HD Graphics 400',2,'WINDOWS 64 BIT 6.2.9200','','MHz (z pliku): 1,6 Ghz',NULL,1600.0,'R10','Dell ChromeBook 11 3180','','Dell ChromeBook 11 3180 Intel(R) Celeron(R) CPU N3060 @ 1.60GHz.txt','Windows','6.2.9200','9200',1218.0,'CB-CPU',1837.0,'CB-CPU',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',1536.0,'CB-GFX','2026-11-01T14:40:32.379Z');
INSERT INTO "results" VALUES(61,'2024','Intel Core i3-7020U CPU','Intel(R) HD Graphics 620',4,'Windows 10, 64 Bit, Professional Edition (build 19045)','','',2,2310.0,'2024.100','','64 Bit','2024_100_2C_4T_2310_Intel_Core_i3_7020U_CPU_64_Bit.txt','Windows','10','19045',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'',NULL,'','2026-11-01T15:31:42.333Z');
CREATE INDEX idx_results_hardware ON results(edition, cpu, gpu);
COMMIT;
