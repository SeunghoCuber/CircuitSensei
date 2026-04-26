interface DemoPlanStep {
  step: number;
  title: string;
  instruction: string;
  verification: string;
}

interface DemoStage {
  state: string;
  plan: DemoPlanStep[];
  components: string[];
  currentStep: number;
  verifiedSteps: number[];
  annotationImageSrc: string;
}

export interface DemoTurn {
  userText: string;
  agentText: string;
  stage: DemoStage;
}

const voltageDividerPlan: DemoPlanStep[] = [
  {
    step: 1,
    title: "Place R1",
    instruction: "With power disconnected, place R1 from A10 to A20.",
    verification: "R1 bridges A10 and A20.",
  },
  {
    step: 2,
    title: "Place R2",
    instruction: "Place R2 from B20 to B30, using column 20 as the divider midpoint.",
    verification: "R2 bridges B20 and B30.",
  },
  {
    step: 3,
    title: "Wire Arduino leads",
    instruction: "Connect D9 to B10, A0 to C20, and GND to C30.",
    verification: "D9, A0, and GND reach the annotated breadboard holes.",
  },
];

export const MOCK_DEMO_INITIAL_STAGE: DemoStage = {
  state: "MOCK DEMO",
  plan: [],
  components: ["Arduino UNO demo kit", "Breadboard", "Resistors and jumper wires"],
  currentStep: 0,
  verifiedSteps: [],
  annotationImageSrc: "/mock-demo-annotations/voltage-divider-step-0.svg",
};

export const MOCK_DEMO_TURNS: DemoTurn[] = [
  {
    userText: "I want to build a simple Arduino voltage divider.",
    agentText:
      "Great. We'll build a two-resistor voltage divider that the Arduino UNO can drive from D9 and read on A0. I found the demo kit: Arduino UNO, breadboard, R1 1 kOhm, R2 2.2 kOhm, and three jumpers. Step 1: keep power disconnected and place R1 from A10 to A20.",
    stage: {
      state: "INSTRUCT",
      plan: voltageDividerPlan,
      components: [
        "Arduino UNO",
        "Full-size breadboard",
        "R1: 1 kOhm resistor",
        "R2: 2.2 kOhm resistor",
        "Jumpers: D9, A0, GND",
      ],
      currentStep: 0,
      verifiedSteps: [],
      annotationImageSrc: "/mock-demo-annotations/arduino_uno.png",
    },
  },
  {
    userText: "R1 is in place.",
    agentText:
      "Nice. In the live demo, Circuit Sensei would verify that resistor with the camera. For this scripted example, R1 is marked complete. Next, place R2 from B20 to B30 so it shares the midpoint at column 20.",
    stage: {
      state: "INSTRUCT",
      plan: voltageDividerPlan,
      components: [
        "R1 placed: 1 kOhm resistor",
        "Next: R2 2.2 kOhm resistor",
        "Remaining jumpers: D9, A0, GND",
      ],
      currentStep: 1,
      verifiedSteps: [1],
      annotationImageSrc: "/mock-demo-annotations/arduino_uno-copy.png",
    },
  },
  {
    userText: "R2 is placed too.",
    agentText:
      "That completes the divider body. Now wire the Arduino UNO test leads: D9 to B10 for the drive signal, A0 to C20 to sense the midpoint, and GND to C30 for the return.",
    stage: {
      state: "INSTRUCT",
      plan: voltageDividerPlan,
      components: [
        "R1 placed",
        "R2 placed",
        "Next: D9 to B10",
        "Next: A0 to C20",
        "Next: GND to C30",
      ],
      currentStep: 2,
      verifiedSteps: [1, 2],
      annotationImageSrc: "/mock-demo-annotations/arduino_uno-copy-2.png",
    },
  },
  {
    userText: "The Arduino jumpers are connected.",
    agentText:
      "Excellent. The scripted visual check passes: D9 reaches the top of R1, A0 reaches the midpoint, and GND reaches the bottom of R2. The circuit is ready for the Arduino measurement.",
    stage: {
      state: "VERIFY_COMPLETE",
      plan: voltageDividerPlan,
      components: [
        "R1 placed",
        "R2 placed",
        "D9 -> B10",
        "A0 -> C20",
        "GND -> C30",
      ],
      currentStep: 2,
      verifiedSteps: [1, 2, 3],
      annotationImageSrc: "/mock-demo-annotations/arduino_uno-copy-2.png",
    },
  },
  {
    userText: "Run the test.",
    agentText:
      "Mock Arduino test complete: D9 HIGH produced an A0 reading around 3.4 V, which matches a 1 kOhm over 2.2 kOhm divider on a 5 V signal. Visit our table for the full live demo on a real Arduino UNO.",
    stage: {
      state: "TEST",
      plan: voltageDividerPlan,
      components: [
        "Arduino UNO connected",
        "Voltage divider verified",
        "D9 source: HIGH",
        "A0 reading: about 3.4 V",
      ],
      currentStep: 2,
      verifiedSteps: [1, 2, 3],
      annotationImageSrc: "/mock-demo-annotations/arduino_uno-copy-2.png",
    },
  },
];

export const MOCK_DEMO_REPEAT_TURN: DemoTurn = {
  userText: "Can I try the real setup next?",
  agentText:
    "Yes. This pre-generated example is complete; visit our table and we will run the full Circuit Sensei demo with the Arduino UNO, camera verification, and live measurements.",
  stage: MOCK_DEMO_TURNS[MOCK_DEMO_TURNS.length - 1].stage,
};
