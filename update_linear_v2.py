#!/usr/bin/env python3
"""Gera os 6 arquivos cp_l_linear_v2_*.json enriquecidos com dados do esquema 8167762 (Rev V08)."""

import json

STATIONS = [
    {"name": "MAGFRONT", "number": 1, "role": "Material Provisioning - Front Covers"},
    {"name": "MEAS",     "number": 2, "role": "Measurement and Quality Check"},
    {"name": "iDRILL",   "number": 3, "role": "Assembly - Drilling"},
    {"name": "MAGBACK",  "number": 4, "role": "Material Provisioning - Back Covers"},
    {"name": "MPRESS",   "number": 5, "role": "Assembly - Press Fitting"},
    {"name": "OUT",      "number": 6, "role": "Workpiece Output"},
]

# Filename suffix matches existing files (lowercase)
STATION_FILE_SUFFIX = {
    "MAGFRONT": "magfront",
    "MEAS":     "meas",
    "iDRILL":   "idrill",
    "MAGBACK":  "magback",
    "MPRESS":   "mpress",
    "OUT":      "out",
}


def prop(id_short, value_type, value, semantic_id=None):
    p = {"modelType": "Property", "idShort": id_short, "valueType": value_type, "value": value}
    if semantic_id:
        p["semanticId"] = {"type": "ExternalReference", "keys": [{"type": "GlobalReference", "value": semantic_id}]}
    return p


def coll(id_short, elements):
    return {"modelType": "SubmodelElementCollection", "idShort": id_short, "submodelElements": elements}


def build_aas(station):
    name   = station["name"]
    number = station["number"]
    role   = station["role"]

    base_urn     = f"urn:festo:cp-factory"
    aas_id       = f"{base_urn}:aas:CP-L-LINEAR-V2-{name}"
    asset_id     = f"{base_urn}:asset:CP-L-LINEAR-V2-{name}"
    sm_nameplate = f"{base_urn}:sm:CP-L-LINEAR-V2-{name}:Nameplate"
    sm_tech      = f"{base_urn}:sm:CP-L-LINEAR-V2-{name}:TechnicalData"
    sm_doc       = f"{base_urn}:sm:CP-L-LINEAR-V2-{name}:Documentation"

    aas = {
        "assetAdministrationShells": [{
            "modelType": "AssetAdministrationShell",
            "id": aas_id,
            "idShort": f"AAS_CP_L_LINEAR_V2_{name}",
            "displayName": [{"language": "en", "text": f"Linear V2 - Conveyor for station {name}"}],
            "assetInformation": {"assetKind": "Instance", "globalAssetId": asset_id},
            "submodels": [
                {"type": "ModelReference", "keys": [{"type": "Submodel", "value": sm_nameplate}]},
                {"type": "ModelReference", "keys": [{"type": "Submodel", "value": sm_tech}]},
                {"type": "ModelReference", "keys": [{"type": "Submodel", "value": sm_doc}]},
            ]
        }],
        "submodels": [
            # ── Nameplate ──────────────────────────────────────────────────────────
            {
                "modelType": "Submodel",
                "id": sm_nameplate,
                "idShort": "Nameplate",
                "semanticId": {"type": "ExternalReference", "keys": [{"type": "GlobalReference",
                    "value": "https://admin-shell.io/zvei/nameplate/2/0/Nameplate"}]},
                "submodelElements": [
                    prop("ManufacturerName", "xs:string", "Festo Didactic SE",
                         "0173-1#02-AAO677#002"),
                    prop("ManufacturerProductDesignation", "xs:string", "Linear V2 Conveyor"),
                    prop("ManufacturerArticleNumber", "xs:string", "D12501"),
                    prop("ManufacturerOrderCode", "xs:string", "CP-L-LINEAR-V2-C11M0"),
                    prop("InstanceName", "xs:string", f"LINEAR-{name}"),
                    prop("StationNumber", "xs:int", str(number)),
                    prop("StationRole", "xs:string", role),
                    prop("CountryOfOrigin", "xs:string", "Canada"),
                    prop("ServicePortal", "xs:string", "https://ip.festo-didactic.com"),
                ]
            },
            # ── TechnicalData ──────────────────────────────────────────────────────
            {
                "modelType": "Submodel",
                "id": sm_tech,
                "idShort": "TechnicalData",
                "semanticId": {"type": "ExternalReference", "keys": [{"type": "GlobalReference",
                    "value": "https://admin-shell.io/ZVEI/TechnicalData/Submodel/1/2"}]},
                "submodelElements": [
                    coll("GeneralInformation", [
                        prop("ProductFamily",   "xs:string", "CP Lab"),
                        prop("ProductCategory", "xs:string", "Base module / Conveyor"),
                        prop("SchematicsDocument", "xs:string", "8167762 Rev V08"),
                    ]),
                    coll("TechnicalProperties", [
                        prop("OperatingVoltage_DC",  "xs:string", "24 VDC"),
                        prop("OperatingPressure_bar","xs:float",  "6.0"),
                        prop("DimensionHeight_mm",   "xs:int",    "700"),
                        prop("DimensionWidth_mm",    "xs:int",    "350"),
                        prop("DimensionDepth_mm",    "xs:int",    "205"),
                    ]),
                    # ── PLC Hardware ───────────────────────────────────────────────
                    coll("PLCHardware", [
                        prop("CPU_Model",         "xs:string", "Siemens ET200SP CPU 1512SP F-1PN"),
                        prop("CPU_OrderCode",     "xs:string", "6ES7512-1SK00-0AB0"),
                        prop("CPU_NetworkAddress","xs:string", "192.168.0.1"),
                        prop("DI_Module_1",       "xs:string", "Siemens DI 8x24VDC (6ES7131-6BF00-0CA0)"),
                        prop("DI_Module_2",       "xs:string", "Siemens DI 8x24VDC (6ES7131-6BF00-0CA0)"),
                        prop("DQ_Module_1",       "xs:string", "Siemens DQ 8x24VDC 0.5A (6ES7132-6BF00-0CA0)"),
                        prop("DQ_Module_2",       "xs:string", "Siemens DQ 8x24VDC 0.5A (6ES7132-6BF00-0CA0)"),
                        prop("IOLink_CM",         "xs:string", "Siemens CM 4x IO-Link ST (6ES7137-6BD00-0BA0)"),
                        prop("EthernetSwitch",    "xs:string", "Siemens Scalance XB008 - 8x RJ45 10/100Mbit unmanaged"),
                        prop("PowerSupply",       "xs:string", "24 VDC / 2 A"),
                    ]),
                    # ── HMI ────────────────────────────────────────────────────────
                    coll("HMI", [
                        prop("Model",       "xs:string", "Siemens SIMATIC MTP700"),
                        prop("ArticleNumber","xs:string", "8189692"),
                        prop("Interface",   "xs:string", "Ethernet (X5), USB (X6)"),
                        prop("Buttons",     "xs:string", "SF1-SF5 (Start, Stop, F1, F2, Reset)"),
                        prop("Indicators",  "xs:string", "PF1-PF4 (signal lamps)"),
                    ]),
                    # ── RFID ───────────────────────────────────────────────────────
                    coll("RFID", [
                        prop("Model",          "xs:string", "Siemens RF210R"),
                        prop("Protocol",       "xs:string", "IO-Link V1.1"),
                        prop("IOLink_Port",    "xs:int",    "1"),
                        prop("IO_ByteSize",    "xs:int",    "32"),
                        prop("ReadPayload_B",  "xs:int",    "28"),
                        prop("StatusBits",     "xs:string", "TagPresent (%I40.0), Error (%I40.1), Done (%I40.2)"),
                        prop("CmdWrite",       "xs:string", "%Q40.0 + 28 byte payload"),
                        prop("CmdRead",        "xs:string", "%Q40.1"),
                    ]),
                    # ── Motor and Encoder ──────────────────────────────────────────
                    coll("MotorEncoder", [
                        prop("Motor_Model",          "xs:string", "OTT#SWM4033438-3"),
                        prop("Motor_Voltage",        "xs:string", "24 VDC bidirectional (normal/reduced speed)"),
                        prop("Encoder_Model",        "xs:string", "Festo FES.102796"),
                        prop("Encoder_PulsesPerCh",  "xs:int",    "8"),
                        prop("Encoder_mmPerRotation","xs:float",  "94.2"),
                        prop("Encoder_Calculation",  "xs:string", "30mm dia × π = 94.2 mm/rotation at 8 pulses/ch"),
                        prop("Encoder_Connector_A",  "xs:string", "BNC X18 (channel A - BG7)"),
                        prop("Encoder_Connector_B",  "xs:string", "BNC X19 (channel B - BG8)"),
                    ]),
                    # ── Pneumatics ─────────────────────────────────────────────────
                    coll("Pneumatics", [
                        prop("StopperValve_Model",   "xs:string", "VUVG-L10-M52-MT-M5-1P3"),
                        prop("StopperValve_FestoPN", "xs:string", "FES.574351"),
                        prop("StopperValve_Type",    "xs:string", "5/2 monostable, 24 VDC solenoid"),
                        prop("StopperSensor_BG9",    "xs:string", "Lower/press position sensor → %I42.7"),
                    ]),
                    # ── IO Summary ─────────────────────────────────────────────────
                    coll("IO_Configuration", [
                        prop("DigitalInputs_Byte0",   "xs:int", "8",  "App inputs DI0-DI7 from KF2"),
                        prop("DigitalInputs_Byte1",   "xs:int", "8",  "Control panel inputs from KF3"),
                        prop("DigitalInputs_Byte42",  "xs:int", "8",  "IO-Link sensors BG1-BG4, KG1-KG2, GF1, BG9"),
                        prop("DigitalOutputs_Byte0",  "xs:int", "8",  "App outputs DQ0-DQ7 from KF4"),
                        prop("DigitalOutputs_Byte1",  "xs:int", "8",  "Control panel outputs from KF5"),
                        prop("DigitalOutputs_Byte42", "xs:int", "8",  "IO-Link actuator outputs"),
                        prop("AnalogInputs_WordIW43", "xs:int", "1",  "App_AI0 (IO-Link analog)"),
                        prop("AnalogInputs_WordIW46", "xs:int", "1",  "App_AI1 (IO-Link analog)"),
                        prop("AnalogOutputs_WordQW43","xs:int", "1",  "App_AO0 (IO-Link analog)"),
                        prop("AnalogOutputs_WordQW45","xs:int", "1",  "App_AO1 (IO-Link analog)"),
                    ]),
                    # ── IO Mapping ─────────────────────────────────────────────────
                    coll("IO_Mapping", [
                        coll("Byte0_ApplicationInterface", [
                            prop("I0_0_App_DI0", "xs:boolean", "false"),
                            prop("I0_1_App_DI1", "xs:boolean", "false"),
                            prop("I0_2_App_DI2", "xs:boolean", "false"),
                            prop("I0_3_App_DI3", "xs:boolean", "false"),
                            prop("I0_4_App_DI4", "xs:boolean", "false"),
                            prop("I0_5_App_DI5", "xs:boolean", "false"),
                            prop("I0_6_App_DI6", "xs:boolean", "false"),
                            prop("I0_7_App_DI7", "xs:boolean", "false"),
                            prop("Q0_0_App_DQ0", "xs:boolean", "false"),
                            prop("Q0_1_App_DQ1", "xs:boolean", "false"),
                            prop("Q0_2_App_DQ2", "xs:boolean", "false"),
                            prop("Q0_3_App_DQ3", "xs:boolean", "false"),
                            prop("Q0_4_App_DQ4", "xs:boolean", "false"),
                            prop("Q0_5_App_DQ5", "xs:boolean", "false"),
                            prop("Q0_6_App_DQ6", "xs:boolean", "false"),
                            prop("Q0_7_App_DQ7", "xs:boolean", "false"),
                        ]),
                        coll("Byte1_ControlPanel", [
                            prop("I1_0_Start",       "xs:boolean", "false"),
                            prop("I1_1_Stop",        "xs:boolean", "false"),
                            prop("I1_2_F1",          "xs:boolean", "false"),
                            prop("I1_3_F2",          "xs:boolean", "false"),
                            prop("I1_4_Reset",       "xs:boolean", "false"),
                            prop("I1_5_Automatic",   "xs:boolean", "false"),
                            prop("I1_6_RI",          "xs:boolean", "false"),
                            prop("I1_7_Auto",        "xs:boolean", "false"),
                            prop("Q1_0_IO_Lamp",     "xs:boolean", "false"),
                            prop("Q1_1_PF1_Lamp",    "xs:boolean", "false"),
                            prop("Q1_2_PF2_Lamp",    "xs:boolean", "false"),
                            prop("Q1_3_PF3_Lamp",    "xs:boolean", "false"),
                            prop("Q1_4_PF4_Lamp",    "xs:boolean", "false"),
                            prop("Q1_5_Conveyor_Fwd","xs:boolean", "false"),
                            prop("Q1_6_Conveyor_Bwd","xs:boolean", "false"),
                            prop("Q1_7_MB1",         "xs:boolean", "false"),
                        ]),
                        coll("Byte42_IOLink_Sensors", [
                            prop("I42_0_BG1_CarrierPos1",  "xs:boolean", "false"),
                            prop("I42_1_BG2_CarrierPos2",  "xs:boolean", "false"),
                            prop("I42_2_BG3_CarrierPos3",  "xs:boolean", "false"),
                            prop("I42_3_BG4_CarrierPos4",  "xs:boolean", "false"),
                            prop("I42_4_KG1_CouplingIn",   "xs:boolean", "false"),
                            prop("I42_5_KG2_CouplingOut",  "xs:boolean", "false"),
                            prop("I42_6_GF1_CouplingSet",  "xs:boolean", "false"),
                            prop("I42_7_BG9_StopperDown",  "xs:boolean", "false"),
                            prop("Q42_0_BG1_BCDDisplay_b0","xs:boolean", "false"),
                            prop("Q42_1_BG2_BCDDisplay_b0","xs:boolean", "false"),
                            prop("Q42_2_BG3_BCDDisplay_b0","xs:boolean", "false"),
                            prop("Q42_3_BG4_BCDDisplay_b0","xs:boolean", "false"),
                            prop("Q42_4_CouplingIn_Act",   "xs:boolean", "false"),
                            prop("Q42_5_CouplingOut_Act",  "xs:boolean", "false"),
                            prop("Q42_6_GF1_Release",      "xs:boolean", "false"),
                            prop("Q42_7_Stopper_Retract",  "xs:boolean", "false"),
                        ]),
                        coll("Words_AnalogInterface", [
                            prop("IW43_App_AI0", "xs:int", "0"),
                            prop("IW46_App_AI1", "xs:int", "0"),
                            prop("QW43_App_AO0", "xs:int", "0"),
                            prop("QW45_App_AO1", "xs:int", "0"),
                        ]),
                    ]),
                    # ── Communication ──────────────────────────────────────────────
                    coll("CommunicationProtocols", [
                        prop("PROFINET", "xs:string", "Siemens ET200SP via Scalance XB008 switch"),
                        prop("IOLink",   "xs:string", "IO-Link V1.1 via CM 4x IO-Link ST (4 ports)"),
                        prop("InterModuleCoupling", "xs:string",
                             "Optical 2-bit coupling (KG1/KG2 in, GF1/GF2 out)"),
                    ]),
                ]
            },
            # ── Documentation ──────────────────────────────────────────────────────
            {
                "modelType": "Submodel",
                "id": sm_doc,
                "idShort": "Documentation",
                "semanticId": {"type": "ExternalReference", "keys": [{"type": "GlobalReference",
                    "value": "https://admin-shell.io/DigiWin/ManufacturerDocumentation/0/1/Documentation"}]},
                "submodelElements": [
                    coll("OperatingManual", [
                        prop("Title", "xs:string", "CP-L-LINEAR-V2 Operating Manual"),
                        {"modelType": "File", "idShort": "ManualFile", "mimeType": "application/pdf",
                         "value": "https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-L-LINEAR-V2/files/manual_en.pdf"},
                    ]),
                    coll("Schematics", [
                        prop("Title",           "xs:string", "CP-L-LINEAR-V2 Electrical Schematics (8167762 Rev V08)"),
                        prop("SchematicsRevision","xs:string","V08"),
                        {"modelType": "File", "idShort": "SchematicsFile", "mimeType": "application/pdf",
                         "value": "https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-L-LINEAR-V2/files_C11M0/schematics.pdf"},
                    ]),
                    coll("MaintenanceManual", [
                        prop("Title", "xs:string", "CP Factory Maintenance Manual 2023"),
                        {"modelType": "File", "idShort": "MaintenanceFile", "mimeType": "application/pdf",
                         "value": "https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/common/files/CP-Maintenance_Manual-2023.07-en.pdf"},
                    ]),
                ]
            },
        ],
        "conceptDescriptions": []
    }
    return aas


if __name__ == "__main__":
    import os
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for station in STATIONS:
        suffix = STATION_FILE_SUFFIX[station["name"]]
        path = os.path.join(out_dir, f"cp_l_linear_v2_{suffix}.json")
        data = build_aas(station)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  wrote {path}")
    print("Done.")
