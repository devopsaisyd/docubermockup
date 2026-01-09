import { z } from "zod";

export const RoleSchema = z.enum(["clinic_admin", "clinic_staff", "doctor", "admin"]);
export type Role = z.infer<typeof RoleSchema>;

export const SpecialtySchema = z.enum(["dentist_general", "endodontist", "anesthetist"]);
export type Specialty = z.infer<typeof SpecialtySchema>;

export const VerificationStatusSchema = z.enum(["pending", "approved", "rejected"]);
export type VerificationStatus = z.infer<typeof VerificationStatusSchema>;

export const ShiftStatusSchema = z.enum([
  "draft",
  "posted",
  "booked",
  "en_route",
  "checked_in",
  "completed",
  "paid",
  "canceled",
  "no_show"
]);
export type ShiftStatus = z.infer<typeof ShiftStatusSchema>;

export const MoneyINRSchema = z
  .number()
  .int()
  .min(100, "Minimum ₹100")
  .max(200000, "Maximum ₹200,000");

export const LatSchema = z.number().min(-90).max(90);
export const LngSchema = z.number().min(-180).max(180);

export const OtpTypeSchema = z.enum(["checkin", "checkout"]);
export type OtpType = z.infer<typeof OtpTypeSchema>;

export const AuthOtpRequestSchema = z.object({
  phone: z.string().min(8).max(20)
});

export const AuthOtpVerifySchema = z.object({
  phone: z.string().min(8).max(20),
  otp: z.string().min(4).max(8)
});

export const ShiftCreateSchema = z.object({
  specialty: SpecialtySchema,
  startTime: z.string(),
  endTime: z.string(),
  payAmountINR: MoneyINRSchema,
  address: z.string().min(5).max(300),
  lat: LatSchema,
  lng: LngSchema,
  notes: z.string().max(1000).optional(),
  autoReplace: z.boolean().default(false)
});

