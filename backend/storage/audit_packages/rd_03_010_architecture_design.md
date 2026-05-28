Hardware Requirement and Design Specification

[Project Name]

**Revision History**

* 在此文件中有任何變動，文件撰寫者須進行小版次[y]的進版，並在說明欄位填寫與前一版之差異。

Any adjustment in this document, editor should update the version of [y] and clarify the difference between previous version.

* 大版號[x]之變動，由CM經理依據基準完成後進行調整。說明欄位須將此基準審查JIRA單號列入。

The version of [x] adjustment, CM manager should adjust after baseline process is completed, should fill out the JIRA No. into the description column.

* 視需求，可自行增加欄位

Extend, as necessary.

| Revision | Date | Description | Author |
| --- | --- | --- | --- |
| [x.y] | YYYY/MM/DD | Detail change information | Name |
|  |  |  |  |

|  |
| --- |
| * **[綠色]中的句子表示不屬於目前交付的可交付成果，需填入實際成果名稱**   **The sentences in [Green] represent the deliverables that are not part of current delivery. Should fill out the actual deliverables.** |
| * **使用您的專案資料完成本文內容**   **Complete below all contents with your project information** |
| * **內文請用英文撰寫為主**   **Please write the main text primarily in English.** |
| * **刪除空白表格與欄位**   **Delete empty tables** |
| * **完成時，須把所有文字轉成黑體並刪除所有以項目符號開頭的綠色說明**   **Upon completion, all text must be converted to bold, and all green bullet-pointed notes must be deleted.** |

# Hardware Basic Design

Provide an overview of the basic hardware design philosophy and non-safety-related functional design. / 概述硬體的基本設計理念和非安全相關的功能設計。

## Hardware architecture block diagram

Draw a high-level block diagram of the product's hardware architecture. The diagram should include all major functional units (e.g., MCU, Power Supply, Communication Interfaces, Sensors/Actuators) and their interconnections. / 繪製產品硬體架構的高階方塊圖。圖中應包含所有主要功能單元（如 MCU, Power Supply, Communication Interfaces, Sensors/Actuators）及其相互連接關係。

The purpose of this work process is to perform basic design on the hardware level based on the system block diagram defined in the system design in Part 4, excluding safety mechanisms.

## Hardware design

Describe the detailed hardware design, including key component selection, circuit design principles, power management scheme, and clocking scheme. / 描述硬體設計的詳細內容，包括關鍵元件選型、電路設計原則、電源管理方案、時脈方案等。

### Summary of hardware components (basic functions)

|  |  |  |  |
| --- | --- | --- | --- |
| HW ID | Focus Elements | Function and requirement description | Safety related (Y/N) |
| **HW ID of focus element.** | **Focus element name.** | **Non-safety function and requirements of focus elements.** | **Is the focus element related to safety** |
| HW-001 | PCIe PHY | ．PCIe protocal handling  ．Transmit Application Control | Y |
| HW-002 | PCIe MAC | ．PCIe protocol handling  ．Transmit Application Control | Y |
| HW-003 | NVMe | ．NVNe | Y |
|  |  |  |  |

### Focus element (basic functions)

#### Hardware Design

Introduction of focus elements, each focus elements topic including following sections :

##### [Focus element(HW-ID)]

###### Overview

This section enumerates the focus element’s basic description.

###### Function

This section enumerates the focus element’s functions.

##### NVMe(HW-003)

###### **Overview**

The NVM Express (NVMe) interface allows host software to communicate with a non-volatile memory subsystem. NVM Express is a register level interface that allows the PCIe host software to communicate with SSD. The NVMe controller comply NVM Express specification version 1.4. The NVMe is the application layer of PCIe protocol.

The NVMe component is connected to PCIe component to communicate with the host, to handle the NVMe commands and dealing with downstream/upstreamd data flow. The NVMe component is also equipped with HMB to perform relate features.

###### **F*unction***

1. SRIOV

SR-IOV is a solution of virtualization. The two types of function are physical function (PF) and virtual function (VF). The NVMe element is equipped with 1 PF, which has the capabilities of SR-IOV, and 8 VF associated with the PF. Each function is equipped with 1 admin queue and 16 queue pair at maximum. Each function could be accessed independently.

1. Admin queue

An Admin Queue is consisted of a pair of Submission Queue and Completion Queue.

Commands submitted to an Admin Queue are Admin commands. Admin commands are used to manage properties of the NVMe subsystem

The following table shows the command requirement and the ability to support by the NVMe controller. The list of commands follows NVMe 1.4 specification.

1. I/O queue

An I/O Queue is consisted of a pair of Submission Queue and Completion Queue.

Commands submitted to a NVM I/O Queue are NVM Commands. NVM I/O Commands are used to manage data in Logical Blocks/Namespaces.

The following table shows the support list by the NVMe controller. The list of commands follows NVMe 1.4 specification.

## Hardware-hardware internal interface

Describe the interface specifications between internal functional units (e.g., MCU and memory, MCU and other chips), including signal definitions, timing requirements, and electrical characteristics. / 描述硬體內部各功能單元之間（例如 MCU 與記憶體、MCU 與其他晶片）的介面規範，包括訊號定義、時序要求、電氣特性等。

列出所有在3.1的block diagram中HW to HW Block之間的Protocol並建立說明。

Interface connected between hardware elements, each hardware-hardware Internal interface topic including following content :

### [HW-to-HW Internal interface]

1. Description :Interface purpose and simple usecase description.
2. Block diagram : Descript interface between blocks such as master and slave and show the direction of signal.
3. Signal description : Descript signal information including signal, width, source, description.

### CFG Protocol

1. Description

CFG (Configuration) protocol is a self-defined protocol, which has a very simple behavior and is easy to used and implemented.

And it is used in register access through whole chip. It is the interface between CPU/FW with overall registers.

1. ![一張含有 文字, 行, 圖表, 字型 的圖片  AI 產生的內容可能不正確。](data:image/png;base64...)Block diagram
2. Signal description

|  |  |  |  |
| --- | --- | --- | --- |
| Signal | Width (Bit) | Source | Description |
| CS | 1 | Master | Enable read/write |
| WR | 1 | Master | Write enable |
| BE | 32 | Master | Byte enable |
| ADDR | 32 | Master | Address selected |
| WDATA | 32 | Master | Write data value |
| RDATA | 32 | Slave | Read data value |
| READY | 1 | Slave | Slave ready signal |

## Hardware-hardware external interface

Describe the interface specifications between the hardware and external systems or components (e.g., wiring harness, other ECUs, sensors, actuators), including connector type, pin definition, electrical characteristics, and communication protocols. / 描述硬體與外部系統或元件之間（例如與線束、其他 ECU、感測器、致動器）的介面規範，包括連接器類型、引腳定義、電氣特性、通訊協議等。

Interface connected between hardware elements and external block, each hardware-hardware external interface topic including following information:

### [Hardware-hardware external interface]

Description of protocol.

| Signal Name | I/O type | Voltage | Description |
| --- | --- | --- | --- |
| Port name | I/O Type (where 'I' denotes Input, 'O' denotes Output). | Voltage value of pin. | Descript signal information. |
|  |  |  |  |

### [PCIe Protocol]

This is the PCIe interface as described [Specification] PCI Express® Base Specification Revision 4.1. It is a bidirectional electric interface which is the main functional interface of our system between the host and our ASIC SSD Controller.

| Signal Name | I/O type | Voltage | Description |
| --- | --- | --- | --- |
| REFCLKn | I | 1.8V | PCIe Reference Clock signals (100 MHz) defined by the PCI Express Base Specification. |
|  |  |  |  |

## Hardware-software interface (HSI) specifications. (basic functions)

Describe the non-safety-related functional interface provided by the hardware for software use. Detail the register addresses, bit definitions, control logic, and data structures. / 描述硬體提供給軟體使用的非安全相關功能介面。應詳細說明暫存器位址、位元定義、控制邏輯、資料結構等。

Interface connected between hardware element and software element, each hardware-hardware Internal interface topic aim to descript purpose of interface and simple use case description.

### [Hardware-software interface]

Description of HSI and related functions

### NVMe Reg I/F

* NVMe\_EPO

NVMe\_EPO is responsible for command fetch, parsing, completion processing and read/write data transferring. All the Host interface register locate in NVMe\_EPO as well.

* NVMe\_Bridge

NVMe\_Bridge schedules the internal data transfer.

* AES

AES is responsible for encryption and decryption of user data to prevent it from user information leaking.

* HMB

Host Memory Buffer (HMB) provides NVMe element capabilities to utilize host memory as cache.

## Interaction and state of component functions

Describe the behavior and interaction logic of the hardware's functional units during different operating modes or state transitions. State diagrams or timing diagrams can be used for illustration. / 描述硬體各功能單元在不同操作模式或狀態轉換時的行為和互動邏輯。可使用狀態圖或時序圖輔助說明。

* 本節旨在描述硬體架構圖中各元件之間的事件順序和互動。它可以使用 UML 圖或文字描述來呈現。如果包含 UML 圖，則必須附加其對應的文字檔案。

This section aims to describe the sequence of events and interactions among the components in the hardware architecture diagram. It can be presented using UML diagrams or a textual description.

If a UML diagram is included, its corresponding text file must be attached.

Introduction of focus elements, each focus elements topic including following sections:

### [Interaction flow section]

#### Overview

This section enumerates interaction and state basic description.

#### Flow

This section enumerates the interaction flow, It can be presented using UML diagrams or a textual description. If a UML diagram is included, its corresponding text file must be attached.

### Admin and I/O Command flow

#### Overview

This section describes the admin command processes. The command flow is divided into three catagories: Admin Command with No Data Process, Admin Command with Downstream Data Process and Admin Command with Upstream Data Process, regarding with the data flow of commands.

#### Flow

Admin commands with no data transfer, changing NVMe configurations only. For example, a Create Submission Queue command.

![一張含有 文字, 行, 圖表, 數字 的圖片  AI 產生的內容可能不正確。](data:image/png;base64...)The following figure shows the dynamic flow of an admin command with no data transfer. The NVMe block is the functional component in NVMe element, which is created in order to seperate the interfaces and functional units. Thus, the component is not able to find in static chart.

# Hardware Safety Design

Describe the hardware safety design solutions adopted to satisfy the HSRs defined in Chapter 3. / 描述為滿足第 3 章定義的 HSR 所採用的硬體安全設計方案。

The purpose of this work process is to arrange into the hardware architecture design the hardware architecture diagram created for each safety goal in “HW safety requirement specifications”. Hardware components of safety functions are added to the hardware architecture diagram defined in “Hardware architecture design (basic functions)”.

## Hardware architecture block diagram (with safety functions)

Draw the hardware architecture diagram including safety mechanisms. Clearly indicate safety-related components, safety mechanisms (e.g., redundancy, monitoring circuits), and their relationship with basic functional units. / 繪製包含安全機制的硬體架構圖。應標示出安全相關的元件、安全機制（如冗餘、監控電路）及其與基本功能單元的關係。

Enter safety functions for each safety goal and arrange them into a single diagram of hardware architecture.

## Hardware-software interface (HSI) specifications. (safety functions)

Describe the safety-related functional interface provided by the hardware for software use. Detail the registers, bit definitions, and control logic used for safety mechanism control, fault diagnosis, and safety state reading. / 描述硬體提供給軟體使用的安全相關功能介面。應詳細說明用於安全機制控制、故障診斷、安全狀態讀取的暫存器、位元定義和控制邏輯。

Interface connected between hardware element and software element, each hardware-software interface topic aim to describe purpose of interface and simple use case description.

### [Hardware-software interface]

Safety related HSI interface description.

|  |  |  |  |
| --- | --- | --- | --- |
| base\_address | Begin | End | description |
| Starting address of the 4GB address space | Start offset address | End offset address | Interface description of address region |

### NVMe Reg I/F

NVMe\_CRC is responsible for end-to-end error logging. If a parity mismatch is detected during data processing through the NVMe CRC function, the mechanism records the corresponding failure details.

|  |  |  |  |
| --- | --- | --- | --- |
| base\_address | Begin | End | description |
| 2408\_0000h | 0x1848 | 0x184D | 2-bit detection location |
| 2408\_0000h | 0x184E | 0x18F | 1-bit detection location |

## Hardware safety design

Detail the specific hardware design solutions adopted to implement each HSR, including circuit diagrams, component selection, considerations for Diagnostic Coverage (DC), and fault tolerance mechanisms. / 詳細描述為實現每個 HSR 所採用的具體硬體設計方案，包括電路圖、元件選型、診斷覆蓋率（DC）的考量、故障容忍機制等。

### Summary of hardware components (safety functions)

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Internal Safety Mechanism | | | | |
| Safety Mechanism ID | Safety Mechanism | Function and requirement description | HW implemented | Source HSR ID |
| ID of safety mechanism. | Technological approaches adopted by safety mechanisms | Safety function and requirement of focus element. | HW ID of focus element. | Hardware safety requirements allocated to focus element |
| SM-001 | LCRC | CRC Function  ．Generate and compare crc parity for detection of data bit flips. | HW-001 | HSR1  HSR2 |
| SM-002 | CRC | CRC Checker:  ．Generate and compare crc parity for detection of data bit flips. | HW-002 | HSR3 |
|  |  |  |  |  |

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| External Safety Mechanism | | | | |
| Safety Mechanism ID | Safety Mechanism | Function and requirement description | HW implemented | Source HSR ID |
| ID of safety mechanism. | Technological approaches adopted by safety mechanisms | Safety function and requirement of focus element. | HW ID of focus element. | Hardware safety requirements allocated to focus element |
| EX-SM-001 | Watch Dog | Watch Dog:  ．Wait command ack to reset or abort after 5ms. | Host | HSR4 |
|  |  |  |  |  |

### Internal Safety Mechanism

#### [Internal Safety Mechanism] (SM-ID)

##### Overview

Describe the basic principles of the safety mechanism and its protection method; Create a basic block diagram illustrating the operation of the safety mechanism, including the data flow and control flow

##### Features and diagnostic coverage

Present the safety mechanism along with its protection capabilities.

|  |  |
| --- | --- |
| **Source HSR ID** | Hardware safety requirements allocated to focus element |
| **Hardware component name** | focus element implemented safety mechanism |
| **Frequency of failure detection** | The execution event involved in the mechanism. |
| **Target failure mode** | Description of failure mode that safety mechanism prevented. |
| **ASIL** | The target ASIL level for the requirement. |
| **Safe State** | How to Enter Safe State  (If applicable, please refer to the following options.)   1. Fault Detection Condition 2. Detection Mechanism 3. Trigger Signal   Actions in the Safe State  (If applicable, please refer to the following options.)   1. Error Logging 2. Indication Signals 3. System Limitations 4. Data Backup   How to Exit Safe State  (If applicable, please refer to the following options.)   1. Clearing Conditions 2. Record Retention 3. Recovery Steps |
| **Timing** | ( Follow ISO26262 Part1-3.61 ) ​FDTI: time-span from the occurrence of a fault to its detection. FRTI: time-span from the detection of a fault to reaching a safe state. FTTI: minimum time-span from the occurrence of a fault in an item to a possible occurrence of a hazardous event, if the safety mechanisms are not activated(or no safety mechanism). |
| **Diagnostic Coverage** | Diagnostic coverage provided by safety mechanisms. |
| **Ref.** | Reference document. |

#### NVMe CRC protection ( CRC ) (SM-001)

##### **Overview**

![一張含有 文字, 螢幕擷取畫面, 圖表, 方案 的圖片  AI 產生的內容可能不正確。](data:image/png;base64...)A cyclic redundancy check (CRC) is an error-detection code used to detect bit-flipping errors in transmitted and stored data.

Initially, the CRC encoder generates parity (Parity\_out). The data, combined with parity, is formed into a new word and transmitted along the datapath from NVMe to NAND. This provides robust coverage across the end-to-end data path. Once the data is read, the CRC decoder will recheck for any occurrence of bit flips. The decoder generates parity (Parity\_out') from the data read from the TSB. Subsequently, the decoder compares the two parities (Parity\_out and Parity\_out'). If the parities match, the decoder reports a decode-pass, indicating no bit-flips. If the parities differ, the decoder reports a decode-fail, signifying erroneous bit-flipping.

Each CRC codeword consists of 512 bytes of data and 15 bits of parity.Implement CRC polynomial : x^15+x+1 and Hamming distance is 3, It can detect one- or two-bit errors.

##### Features and diagnostic coverage

|  |  |
| --- | --- |
| **Source HSR ID** | HSR1  HSR2  HSR3  HSR4 |
| **Hardware component name** | NVMe Bridge DMA |
| **Frequency of failure detection** | Each time the host data read out from BUS |
| **Target failure mode** | CRC decoder compares the difference between the parity\_out` with the original one. 1-bit or 2-bit error to be detected will be reported to fw . |
| **ASIL** | B |
| **Safe State** | When E2E fail checked by CRC decoder. Drive returns media UnrecoveredMediaRdErr to host and drive would entry to safe state. |
| **Timing** | ​FDTI <= 1us FRTI <= 1us FTTI <= 1.5us |
| **Diagnostic Coverage** | 99% |
| **Ref.** | ISO 26262-5:2018, D.2.5.6 |

### External Safety Mechanism

* The description is same as 5.2.2.2 Internal Safety Mechanism to add the section and table if needed.

#### [External Safety Mechanism] (SM-ID)

##### Overview

Describe the basic principles of the safety mechanism and its protection method; Create a basic block diagram illustrating the operation of the safety mechanism, including the data flow and control flow

##### Features and diagnostic coverage

Present the technical features of the safety mechanism along with its protection capabilities.

## Interaction and State of component functions(safety functions)

Describe the behavior and interaction logic of the hardware's functional units upon fault occurrence or safety state transition. Specifically explain how safety mechanisms are triggered, executed, and reported. / 描述硬體各功能單元在故障發生或安全狀態轉換時的行為和互動邏輯。應特別說明安全機制如何被觸發、執行和報告狀態。

This section aims to describe the sequence of events and interactions among the components in the hardware architecture diagram which related to safety functions. It can be presented using UML diagrams or a textual description.

If a UML diagram is included, its corresponding text file must be attached.

### [Interaction flow section]

#### Overview

This section enumerates interaction and state basic description.

#### Flow

This section enumerates the interaction flow, It can be presented using UML diagrams or a textual description. If a UML diagram is included, its corresponding text file must be attached.

### Data path protection – frontend

#### Overview

#### Flow

# Hardware design verification

本文件範圍涵蓋硬體需求規格制定與硬體設計，不包含驗證活動的執行與記錄；驗證活動由驗證團隊管理，並記錄於 RD-03-010-03 硬體測試計畫書與 RD-03-010-05 硬體測試案例。

The scope of this document covers hardware requirement specification and hardware design only. Verification activities and execution records are managed by the verification team and documented in RD-03-010-03 Hardware Test Plan and RD-03-010-05 Hardware Test Cases.

Describe the hardware design verification activities to demonstrate that the design satisfies all requirements (functional and safety). / 描述硬體設計的驗證活動，以證明設計滿足所有需求（功能性與安全性）。

## Inspection of technical documents

Specify which technical documents (e.g., schematics, layout drawings, BOM, design reports) will undergo Inspection and Confirmation to ensure compliance with design specifications and standards. / 說明將對哪些技術文件（如電路圖、佈局圖、物料清單、設計報告）進行審查（Inspection）和確認（Confirmation），以確保其符合設計規範和標準。

|  |  |
| --- | --- |
| **Work Product ID** | **Work Product Name** |
| [fill out the WP ID which is defined by CM] | Hardware Requirement and Design Specification Review Checklist |
| [fill out the WP ID which is defined by CM] | Hardware-Software Interface Review Checklist |

## Safety analysis

Describe the safety analysis activities to be performed, such as FMEDA (Failure Modes, Effects, and Diagnostic Analysis) and FTA (Fault Tree Analysis), and specify the scope, methodology, and expected results of the analysis. / 描述將進行的安全分析活動，例如 FMEDA（Failure Modes, Effects, and Diagnostic Analysis）和 FTA（Fault Tree Analysis），並說明分析的範圍、方法和預期結果。

|  |  |
| --- | --- |
| **Work Product ID** | **Work Product Name** |
| [fill out the WP ID which is defined by CM] | DFMEA Report |
| [fill out the WP ID which is defined by CM] | DFA Report |
| [fill out the WP ID which is defined by CM] | FMEDA Report |
| [fill out the WP ID which is defined by CM] | FTA Report  (need to have if ASIL C or ASIL D Product) |

## Cybersecurity verification

HCR 追溯鏈格式與驗證方法選擇依據，請參考 RD-03-010 硬體開發與測試規範 Section 6.2 及 Section 6.4。

HCR traceability chain format and verification method selection shall follow RD-03-010 Hardware Development and Test Instruction Sections 6.2 and 6.4.

此節提供每條 HCR 對應的驗證方式、測試案例 ID、工具環境、通過準則及 TARA 殘餘風險引用。

This section provides the verification method, test case ID, tooling, pass criterion, and TARA residual risk reference for each HCR.

若 HCR 或 TARA 指出 DPA、SPA、side-channel、fault injection 或 debug/test interface 風險適用，驗證計畫應明確列出分析/測試方法、樣品與量測條件、工具或第三方實驗室、通過準則，以及無法測試時的替代證據與理由。

If an HCR or TARA indicates that DPA, SPA, side-channel, fault injection, or debug/test interface risks are applicable, the verification plan shall explicitly list the analysis/test method, sample and measurement conditions, tools or third-party laboratory, pass criteria, and alternative evidence with rationale when direct testing is not feasible.

|  |  |  |  |
| --- | --- | --- | --- |
| **Attack / concern** | **Applicability trigger** | **Expected design evidence** | **Expected verification evidence** |
| DPA / SPA / side-channel leakage | Secret-dependent power/EM/timing behavior, cryptographic operation, key storage or secure boot path | HCR/CC mapping, countermeasure rationale, protected asset boundary | Analysis/test plan, pass criterion, measurement report or documented non-applicability rationale |
| Fault injection / glitch | Security decision, boot/authentication flow, OTP/eFuse read, privilege transition | Fault response behavior, safe/secure state, error logging or lockout behavior | Injection/negative test case or analysis evidence with residual risk reference |
| Debug/test interface abuse | JTAG/TAP, scan chain, test mode, manufacturing access path | Access control, lock state, lifecycle state, production-mode restriction | Access attempt test, register/status evidence, manufacturing control evidence |
|  |  |  |  |

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| HCR-ID | 驗證方式 Verification method | 測試案例 ID Test Case ID (RD-03-010-05) | 工具 / 環境 Tools / environment | 通過準則 Pass criterion | TARA 殘餘風險引用 TARA residual risk ref. |
| HCR-001 | 暫存器檢查 + 測試 Register inspection + test | [HW-TC-Cy-001] | [fill] | No plaintext key on any bus or debug interface 任何匯流排或除錯介面均不得出現明文金鑰 | [TARA Rev. x.y, RT-xx] |
| HCR-002 | 測試（注入竄改映像）Test (inject tampered image) | [HW-TC-Cy-002] | [fill] | Boot halted; tamper event logged 開機停止；竄改事件已記錄 | [TARA Rev. x.y, RT-xx] |
| HCR-003 | 測試（JTAG 存取嘗試）Test (JTAG access attempt) | [HW-TC-Cy-003] | [fill] | JTAG access denied; DBG\_LOCK confirms locked JTAG 存取被拒；DBG\_LOCK 確認已鎖定 | [TARA Rev. x.y, RT-xx] |
