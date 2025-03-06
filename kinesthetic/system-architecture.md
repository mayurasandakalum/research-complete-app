# Kinesthetic Learning System Implementation

The following diagram demonstrates how the fully implemented system processes data and interacts with users in a real classroom environment:

```mermaid
flowchart TD
    %% Real-world interaction
    Student([Student]) -->|Manipulates| PhysObj[Physical Objects]

    %% Physical objects with webcam capture
    subgraph PhysicalInteraction["Physical Interaction Layer"]
        PhysObj --> |Captured by| Webcam[Webcam Stream]
        PhysObj --> AbacusObj[Abacus]
        PhysObj --> ClockObj[Analog Clock]
    end

    %% Image preprocessing
    Webcam --> ImagePrep[Image Preprocessing<br>- Resize: 640x640<br>- Normalization<br>- Background Removal]

    %% Object detection decision
    ImagePrep --> ObjectSelector{Object Type?}
    ObjectSelector -->|Abacus Detected| AbacusPath[Abacus Processing Path]
    ObjectSelector -->|Clock Detected| ClockPath[Clock Processing Path]

    %% Abacus processing implementation
    subgraph AbacusProcessing["Abacus Recognition Pipeline"]
        AbacusPath --> YOLOv11[YOLOv11 Inference<br>OpenVINO INT8]
        YOLOv11 --> BeadDetection[Bead & Stick Detection<br>IoU=0.5, Conf=0.7]
        BeadDetection --> ColumnAssign[Column Assignment Algorithm<br>x-coordinate sorting]
        ColumnAssign --> BeadCount[Bead Counter<br>per column]
        BeadCount --> ValueCalc[Value Calculator<br>Sum of column values]
    end

    %% Clock processing implementation
    subgraph ClockProcessing["Clock Recognition Pipeline"]
        ClockPath --> STN[STN Transformation<br>OpenVINO FP16]
        STN --> AlignedClock[Aligned Clock Image]
        AlignedClock --> ResNet50[ResNet50 Classifier<br>OpenVINO INT8]
        ResNet50 --> TimeClass[Time Classification<br>720 classes]
        TimeClass --> TimeExtract[Time Extraction<br>HH:MM Format]
    end

    %% Feedback system implementation
    ValueCalc --> AnswerCheck{Answer Correct?}
    TimeExtract --> AnswerCheck

    AnswerCheck -->|Yes| PositiveFb[Positive Feedback<br>in Sinhala]
    AnswerCheck -->|No| NegativeFb[Corrective Feedback<br>in Sinhala]

    %% UI Implementation
    subgraph UserInterface["Interactive UI"]
        ExerciseGen[Exercise Generator<br>Addition/Subtraction/Time]
        SinhalaUI[Sinhala Interface]
        ScoreTrack[Score Tracking<br>System]

        ExerciseGen --> SinhalaUI
        PositiveFb --> ScoreTrack
        NegativeFb --> ScoreTrack
    end

    %% System loop implementation
    ScoreTrack -->|Progress Based| ExerciseGen
    PositiveFb --> NextQuestion[Generate Next Question]
    NegativeFb --> RetryOptions[Offer Retry/Hint]
    NextQuestion --> ExerciseGen
    RetryOptions --> SinhalaUI

    %% Database implementation
    subgraph DataStorage["Local Data Storage"]
        LocalDB[(SQLite Database)]
        ConfigFiles[Configuration Files]
        ModelFiles[Optimized Model Files<br>YOLOv11 & STN+ResNet50]
    end

    ScoreTrack --> LocalDB
    LocalDB --> ExerciseGen
    ConfigFiles --> ObjectSelector
    ModelFiles --> YOLOv11
    ModelFiles --> STN
    ModelFiles --> ResNet50

    %% Teacher interface
    subgraph TeacherTools["Teacher Interface"]
        Progress[Progress Dashboard]
        Settings[System Settings]
        ExerciseCustom[Exercise Customization]
    end

    LocalDB --> Progress
    Settings --> ConfigFiles
    ExerciseCustom --> ExerciseGen

    %% Runtime performance monitoring
    subgraph Performance["Runtime Performance"]
        FPS[">30 FPS Processing"]
        Latency["<33ms Response Time"]
        MemUsage["<1GB RAM Usage"]
    end

    YOLOv11 -.-> FPS
    ResNet50 -.-> FPS
    AnswerCheck -.-> Latency
    DataStorage -.-> MemUsage

    %% Styling
    classDef implemented fill:#9cf,stroke:#333,stroke-width:2px
    classDef uiComponent fill:#fcf,stroke:#333,stroke-width:1px
    classDef dataFlow fill:#cfc,stroke:#333,stroke-width:1px
    classDef optimization fill:#ffc,stroke:#333,stroke-width:1px

    class AbacusProcessing,ClockProcessing,TeacherTools implemented
    class UserInterface,SinhalaUI uiComponent
    class ImagePrep,ObjectSelector,AnswerCheck dataFlow
    class Performance,ModelFiles optimization
```

## Implementation Details:

1. **Data Capture & Processing Flow**

   - Student interactions are captured at 30 FPS through a standard webcam
   - Real-time image preprocessing optimizes for detection algorithms
   - Object type determination routes to appropriate processing pipeline

2. **Abacus Processing Implementation**

   - Quantized YOLOv11 detects beads and sticks with 0.888 mAP50-95
   - Column assignment algorithm maps beads to positional values
   - Numeric calculation converts physical configuration to mathematical value

3. **Clock Processing Implementation**

   - STN aligns and corrects perspective distortion in clock images
   - ResNet50 classifies precise hand positions across 720 possible times
   - Time extraction provides digital representation (HH:MM)

4. **User Experience Flow**

   - Sinhala interface presents culturally appropriate exercises
   - Immediate feedback loop maintains student engagement
   - Adaptive difficulty based on performance tracking

5. **System Requirements & Performance**

   - Local database storage for student progress and configuration
   - Optimized models ensure low resource requirements (Intel Core i3/i5)
   - > 30 FPS processing with <33ms response time on standard hardware

6. **Teacher Tools**
   - Progress dashboard for monitoring student advancement
   - Exercise customization to adapt to classroom needs
   - System settings for hardware optimization

This implementation-focused diagram illustrates how the system functions in practice, showing the complete flow from student interaction to educational feedback and progress tracking.
