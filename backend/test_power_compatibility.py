import unittest
import spec_parser as sp
import compat_engine as ce


class PowerCompatibilityTests(unittest.TestCase):
    def build(self, gpu, psu="450W", specs=""):
        return [sp.parse_part("CPU", "AMD RYZEN 5 5500"),
                sp.parse_part("GPU", gpu, specs), sp.parse_part("PSU", "POWER SUPPLY " + psu)]

    def power(self, parts):
        return ce.check_psu_watt(parts)

    def test_5050_requires_550_not_board_draw(self):
        parts = self.build("ASUS PRIME GEFORCE RTX 5050 OC")
        result = self.power(parts)
        self.assertEqual(parts[1]["tdp"], 130)
        self.assertEqual(result["required_watt"], 550)
        self.assertEqual(result["severity"], "ERROR")
        self.assertFalse(result["ok"])
        self.assertTrue(any(s["value"] == 550 and 'nvidia.com' in s["url"] for s in result["sources"]))
        self.assertEqual(self.power(self.build("RTX 5050", "550W"))["severity"], "PASS")

    def test_screenshot_pro5000_is_distinct(self):
        parts = self.build("LEADTEK NVIDIA RTX PRO 5000 BLACKWELL - 48GB GDDR7 WITH ECC")
        self.assertEqual(parts[1]["tdp"], 300)
        self.assertNotIn("recommended_psu_watt", parts[1])
        result = self.power(parts)
        self.assertEqual(result["severity"], "ERROR")
        self.assertEqual(result["required_watt"], 557)
        self.assertIsNone(result["manufacturer_min_watt"])

    def test_unknown_cannot_pass(self):
        for parts in (self.build("Unknown GPU"), self.build("RTX 5050", "unknown"),
                      [sp.parse_part("GPU", "RTX 5050"), sp.parse_part("PSU", "550W")],
                      [sp.parse_part("CPU", "Ryzen 5 5500")], []):
            result = ce.check_build(parts)
            self.assertNotEqual(result["overall"], "ok")
            for check in result["checks"]:
                if check["severity"] == "UNKNOWN":
                    self.assertFalse(check["ok"])

    def test_board_specs_raise_requirement_and_keep_consumption_separate(self):
        specs = 'Recommended PSU:650W\nPower Consumption: 140 W\nSource URL: https://example.com/board'
        parts = self.build("RTX 5050", "550W", specs)
        self.assertEqual(parts[1]["tdp"], 140)
        self.assertEqual(parts[1]["recommended_psu_watt"], 650)
        self.assertNotIn("watt", parts[1])
        self.assertEqual(self.power(parts)["severity"], "ERROR")
        self.assertTrue(any(s["value"] == 650 for s in parts[1]["power_sources"]))

    def test_stacked_retail_details_drive_r9700_and_850w_psu(self):
        gpu_details = """Power Requirement
อัตราการกินไฟ
≈ 300 W
Need Power Supply
750 W
Power Connectors
1 x 16 Pin"""
        psu_details = """PCI Ex Connector
3 x 6+2 Pin
1 x 16 (12V-2x6) Pin
CPU Connector
2 x 4+4 Pin
กำลังไฟสูงสุด
850 W"""
        gpu = sp.parse_part("GPU", "SAPPHIRE RADEON AI PRO R9700 32GB", gpu_details)
        psu = sp.parse_part("PSU", "THERMALTAKE SMART BX3 PRO SE", psu_details)
        self.assertEqual(gpu["tdp"], 300)
        self.assertEqual(gpu["recommended_psu_watt"], 750)
        self.assertEqual(gpu["power_connectors_required"], {"12VHPWR": 1})
        self.assertEqual(psu["watt"], 850)
        self.assertEqual(psu["power_connectors"]["PCIe 8-pin"], 3)
        result = ce.check_build([
            sp.parse_part("CPU", "INTEL CORE I5-14400F LGA1700"), gpu, psu,
        ])
        power = next(c for c in result["checks"] if c["rule"].startswith("R3"))
        connector = next(c for c in result["checks"] if c["rule"].startswith("R8"))
        self.assertEqual(power["severity"], "PASS")
        self.assertEqual(connector["severity"], "PASS")

    def test_sourced_system_requirement_can_pass_without_board_tdp(self):
        gpu = sp.parse_part("GPU", "RADEON AI PRO R9700", "Recommended PSU: 750 W")
        parts = [sp.parse_part("CPU", "INTEL CORE I5-14400F LGA1700"),
                 gpu, sp.parse_part("PSU", "PSU 850W")]
        self.assertEqual(self.power(parts)["severity"], "PASS")

    def test_source_url_numbers_are_not_parsed_as_power(self):
        specs = """Recommended PSU: 750 W
Recommended PSU Source Store: advice
Recommended PSU Source URL: https://example.test/rx-9000-series/card
TDP: 300 W
TDP Source URL: https://example.test/product/9000"""
        gpu = sp.parse_part("GPU", "RADEON AI PRO R9700", specs)
        self.assertEqual(gpu["recommended_psu_watt"], 750)
        self.assertEqual(gpu["tdp"], 300)

    def test_ihave_table_power_requirement_is_mapped_by_category(self):
        gpu = sp.parse_part(
            "GPU", "RTX 5050",
            "Power Requirement\t550 Watt\nPower Connector\t1 x 8-pin",
        )
        psu = sp.parse_part("PSU", "PSU 650W", "Power Requirement\t650 Watt")
        self.assertEqual(gpu["recommended_psu_watt"], 550)
        self.assertEqual(gpu["power_connectors_required"], {"PCIe 8-pin": 1})
        self.assertEqual(psu["watt"], 650)

    def test_rail_power_not_total_psu_rating(self):
        result = sp.parse_part("PSU", "PSU 450W", '+12V rail: 350 W\nOutput voltage: 230 V')
        self.assertEqual(result["watt"], 450)

    def test_desktop_reference_does_not_match_other_models(self):
        for name in ('RTX 50500', 'RTX 5050 Laptop', 'RTX PRO 5000 Ada', 'RTX 5050 Ti'):
            self.assertNotIn('recommended_psu_watt', sp.parse_gpu(name))

    def test_cpu_draw_can_exceed_manufacturer_baseline(self):
        parts = self.build('RTX 5050', '550W')
        parts[0]['tdp'] = 300
        result = self.power(parts)
        self.assertEqual(result['required_watt'], 638)
        self.assertEqual(result['severity'], 'ERROR')

    def test_high_tier_gpu_rule_is_active(self):
        parts = [sp.parse_part('CPU', 'AMD RYZEN 5 7600'),
                 sp.parse_part('GPU', 'RTX 4080'),
                 sp.parse_part('PSU', 'PSU 650W')]
        result = ce.check_build(parts)
        r6 = next(c for c in result['checks'] if c['rule'].startswith('R6'))
        self.assertEqual(r6['severity'], 'WARNING')
        self.assertEqual(r6['required_watt'], 750)
        self.assertEqual(result['overall'], 'warning')

    def test_gpu_psu_connector_is_checked(self):
        gpu = sp.parse_part('GPU', 'RTX 5050')
        self.assertEqual(gpu['power_connectors_required'], {'PCIe 8-pin': 1})
        psu = sp.parse_part('PSU', 'PSU 550W', 'PCIe Connector: 1 x 6+2 pin')
        self.assertEqual(psu['power_connectors'], {'PCIe 8-pin': 1})
        result = ce.check_gpu_power_connectors([gpu, psu])
        self.assertEqual(result['severity'], 'PASS')

    def test_hx1500i_retail_connector_format_is_fully_parsed(self):
        details = ('PCIe Connector: 5 x 6+2-pin, '
                   '2 x 12V-2x6 (12+4) Pin')
        psu = sp.parse_part('PSU', 'PSU CORSAIR HX1500I 1500W', details)
        self.assertEqual(psu['power_connectors'], {
            'PCIe 8-pin': 5, '12V-2x6': 2,
        })
        gpu = sp.parse_part('GPU', 'VGA XFX RADEON RX 9070 GRE',
                            'Power Connectors: 2 x PCIe 8-pin')
        result = ce.check_gpu_power_connectors([gpu, psu])
        self.assertEqual(result['severity'], 'PASS')

    def test_flattened_jib_p650ss_table_keeps_pcie_separate_from_cpu(self):
        details = (
            'Model GP-P650SS Brand Gigabyte specification '
            'PCI Ex Connector 2x 6+2 Pin CPU Connector 2x 4+4 Pin '
            'Mainboard Connector 1x 20+4 Pin กำลังไฟสูงสุด 650 W'
        )
        psu = sp.parse_part('PSU', 'POWER SUPPLY GIGABYTE GP-P650SS 650W', details)
        self.assertEqual(psu['power_connectors'], {'PCIe 8-pin': 2})
        gpu = sp.parse_part('GPU', 'VGA XFX RADEON RX 9070 GRE',
                            'Power Connectors: 2 x PCIe 8-pin')
        self.assertEqual(ce.check_gpu_power_connectors([gpu, psu])['severity'], 'PASS')

    def test_advice_aerocool_lux_summary_has_two_gpu_connectors(self):
        details = ('750W / 80 PLUS BRONZE / Non Modular / Length 160mm / '
                   '1xCPU / 0xPCIe (16 Pin) / 2xPCIe (6+2 Pin)')
        facts = sp.extract_detail_facts('PSU', details)
        self.assertEqual(facts['power_connectors'], {'PCIe 8-pin': 2})
        psu = sp.parse_part('PSU', 'POWER SUPPLY 750W AEROCOOL LUX',
                            'Power Connectors: 2 x 6+2 Pin')
        gpu = sp.parse_part('GPU', 'VGA XFX RADEON RX 9070 GRE',
                            'Power Connectors: 2 x PCIe 8-pin')
        self.assertEqual(ce.check_gpu_power_connectors([gpu, psu])['severity'], 'PASS')

    def test_advice_postfix_connector_count(self):
        details = 'PCIe Power Connector: (6+2 Pin) x 2 Connectors'
        psu = sp.parse_part('PSU', 'PSU 750W', details)
        self.assertEqual(psu['power_connectors'], {'PCIe 8-pin': 2})

    def test_unlisted_connector_type_is_unknown_not_absent(self):
        gpu = sp.parse_part('GPU', 'VGA XFX RADEON RX 9070 GRE',
                            'Power Connectors: 2 x PCIe 8-pin')
        psu = sp.parse_part('PSU', 'PSU 1500W',
                            'Power Connectors: 2 x 12V-2x6')
        result = ce.check_gpu_power_connectors([gpu, psu])
        self.assertEqual(result['severity'], 'UNKNOWN')
        self.assertNotIn('ไม่มีหัวต่อ', result['detail'])

    def test_missing_or_insufficient_connector_never_passes(self):
        gpu = sp.parse_part('GPU', 'RTX 5050')
        missing = ce.check_gpu_power_connectors([gpu, sp.parse_part('PSU', 'PSU 550W')])
        self.assertEqual(missing['severity'], 'UNKNOWN')
        unlisted = sp.parse_part('PSU', 'PSU 550W', 'PCIe Connector: 1 x 6 pin')
        self.assertEqual(ce.check_gpu_power_connectors([gpu, unlisted])['severity'], 'UNKNOWN')
        gpu_needing_two = sp.parse_part('GPU', 'RTX 5050',
                                        'Power Connectors: 2 x PCIe 8-pin')
        one_eight_pin = sp.parse_part('PSU', 'PSU 550W',
                                      'PCIe Connector: 1 x 6+2-pin')
        result = ce.check_gpu_power_connectors([gpu_needing_two, one_eight_pin])
        self.assertEqual(result['severity'], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
