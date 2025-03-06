sequenceDiagram
participant Student
participant System as Learning System
participant Vision as AI Vision System
participant Feedback as Feedback Engine

    System->>Student: Display question in Sinhala
    Student->>Student: Manipulate physical tool (abacus/clock)
    Student->>Vision: Webcam captures interaction

    alt Abacus Question
        Vision->>Vision: YOLOv11 processes image
        Vision->>Vision: Detect sticks and beads
        Vision->>Vision: Calculate numerical value
    else Clock Question
        Vision->>Vision: STN aligns clock image
        Vision->>Vision: ResNet50 classifies time
    end

    Vision->>Feedback: Send detected answer
    Feedback->>Feedback: Compare with expected answer

    alt Correct Answer
        Feedback->>Student: "ඔබේ පිළිතුර නිවැරදියි!" (Your answer is correct!)
        Feedback->>System: Update progress
        System->>Student: Present new question
    else Incorrect Answer
        Feedback->>Student: "ඔබේ පිළිතුර වැරදියි. නැවත උත්සහා කර බලන්න!" (Your answer is incorrect. Please try again!)
        Student->>Student: Adjust physical tool
    end
