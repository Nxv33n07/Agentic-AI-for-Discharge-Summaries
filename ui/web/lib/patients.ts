/**
 * lib/patients.ts — Patient registry. In a real deployment this would come from
 * a backend listing endpoint; for the demo it lists the seed patients and their
 * case descriptions. New patients added under data/patients/<id> would need to
 * be appended here.
 */

export interface PatientInfo {
    id: string;
    name: string;
    age?: number;
    gender?: string;
    admitted?: string;
    summary: string;
    status: "ready" | "draft-available" | "running";
}

export const KNOWN_PATIENTS: PatientInfo[] = [
    {
        id: "patient_001",
        name: "Prema J",
        age: 30,
        gender: "Female",
        admitted: "2026-02-24",
        summary:
            "Acute gastroenteritis with UTI. Full discharge summary present in source notes.",
        status: "ready",
    },
    {
        id: "patient_002",
        name: "H D Nagaraja",
        age: 45,
        gender: "Male",
        admitted: "2026-02-26",
        summary:
            "Acute febrile illness with Type-II DM. Lab results, USG, ECHO present; no discharge summary page (still admitted).",
        status: "ready",
    },
];

export function getPatientInfo(id: string): PatientInfo | undefined {
    return KNOWN_PATIENTS.find((p) => p.id === id);
}
