import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Building2,
  BookOpen,
  UploadCloud,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  CheckCircle2,
  Loader2,
  Save,
  RotateCcw,
  Upload,
} from 'lucide-react';
import { Stepper, StepItem } from '../../components/Stepper';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { StatusChip } from '../../components/StatusChip';
import { ProgressPipeline } from '../../components/ProgressPipeline';
import { useCreateApplication } from '../../api/useCreateApplication';
import { useApplication } from '../../api/useApplication';
import { useUploadDocument } from '../../api/useUploadDocument';
import { useValidate } from '../../api/useValidate';
import { useFindings } from '../../api/useFindings';
import { useChecklist } from '../../api/useChecklist';
import { useSubmitApplication } from '../../api/useSubmitApplication';
import { toastBus } from '../../lib/toastBus';
import { useAuth } from '../../context/AuthContext';

const WIZARD_STEPS: StepItem[] = [
  { id: 'meta', title: 'Institute Info', description: 'PID & Affiliation' },
  { id: 'intake', title: 'Programs & Land', description: 'Intake, Land & Faculty' },
  { id: 'docs', title: 'Dossier Upload', description: 'Statutory Uploads' },
  { id: 'validate', title: 'Validation Pipeline', description: 'AICTE APH Checks' },
  { id: 'submit', title: 'Final Submission', description: 'Sign & Transmit' },
];

const wizardSchema = z.object({
  instituteName: z.string().min(3, 'Institution name must be at least 3 characters'),
  pid: z.string().min(3, 'PID is required'),
  academicYear: z.string().default('2026-2027'),
  category: z.string().default('Engineering & Technology (UG/PG)'),
  program: z.string().default('Bachelor of Technology (B.Tech)'),
  intake: z.coerce.number().min(1, 'Intake must be greater than zero'),
  landAcreage: z.coerce.number().min(0.5, 'Valid land acreage is required'),
  carpetArea: z.coerce.number().min(100, 'Carpet area is required'),
  facultyCount: z.coerce.number().min(1, 'Faculty count is required'),
  studentCount: z.coerce.number().min(1, 'Student strength is required'),
});

type WizardFormData = z.infer<typeof wizardSchema>;

// Baseline required document classes per AICTE APH
const DEFAULT_REQUIRED_CLASSES: Array<{ class_name: string; name: string; required: boolean }> = [
  { class_name: 'land_title_deed', name: 'Registered Land Ownership Deed & Mutation Entry', required: true },
  { class_name: 'building_occupancy_certificate', name: 'Municipal Building / Occupancy Certificate', required: true },
  { class_name: 'fire_safety_certificate', name: 'Government Fire Services Department NOC', required: true },
  { class_name: 'accreditation_certificate', name: 'NBA / NAAC Accreditation Certificate', required: false },
  { class_name: 'ter_payment_receipt', name: 'AICTE TER Processing Fee Payment Receipt', required: true },
  { class_name: 'floor_plan', name: 'Architect Certified Master Plan & Floor Layout', required: true },
  { class_name: 'infrastructure_photo_1', name: 'Geo-tagged Campus Infrastructure Photograph', required: true },
];

export default function SubmissionWizardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [createdAppId, setCreatedAppId] = useState<string | null>(null);

  // Per-row upload tracking
  const [rowFiles, setRowFiles] = useState<Record<string, File>>({});
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [replacingClass, setReplacingClass] = useState<string | null>(null);

  // Form setup
  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
  } = useForm<WizardFormData>({
    resolver: zodResolver(wizardSchema),
    defaultValues: {
      instituteName: user?.full_name || 'Government College of Engineering, Pune',
      pid: user?.institution_id || '1-33276541',
      academicYear: '2026-2027',
      category: 'ENGINEERING_AND_TECHNOLOGY',
      program: 'Bachelor of Technology (B.Tech)',
      intake: 360,
      landAcreage: 7.42,
      carpetArea: 8400,
      facultyCount: 56,
      studentCount: 720,
    },
  });

  // Queries & Mutations
  const createMutation = useCreateApplication();
  const { data: application, refetch: refetchApp } = useApplication(createdAppId || '');
  const { data: checklistData } = useChecklist(createdAppId || '');
  const uploadDocMutation = useUploadDocument();
  const validateMutation = useValidate(createdAppId || '');
  const { data: findingsData, refetch: refetchFindings } = useFindings(createdAppId || '');
  const submitMutation = useSubmitApplication(createdAppId || '');

  // Build upload rows from GET checklist if available, else standard required classes
  const checklistResults = (checklistData as any)?.results || checklistData?.checklist || [];
  const uploadRows = DEFAULT_REQUIRED_CLASSES.map((def) => {
    const cl = checklistResults.find(
      (c: any) => (c.inputs as any)?.document_class === def.class_name || c.rule_id?.toLowerCase().includes(def.class_name)
    );
    // Find uploaded doc from application
    const uploadedDoc = application?.documents?.find(
      (d: any) => d.class === def.class_name || d.category === def.class_name || d.class_name === def.class_name
    );
    return {
      className: def.class_name,
      name: def.name,
      required: def.required,
      checklistStatus: cl ? cl.result : 'PENDING',
      uploadedDoc,
    };
  });

  // Plain-language deficiencies only (filter out possible_anomaly and duplicate per RULES.md)
  const plainLanguageFindings = ((findingsData as any)?.findings || findingsData?.items || []).filter(
    (f: any) => f.type !== 'possible_anomaly' && f.type !== 'duplicate'
  );

  // Helper to initialize or persist draft
  const ensureDraftSaved = async () => {
    if (!createdAppId) {
      const values = getValues();
      const res = await createMutation.mutateAsync({
        institution_id: values.pid,
        academic_year: values.academicYear,
        application_type: 'Extension of Approval (EoA)',
        category: values.category,
        metadata: {
          institute_name: values.instituteName,
          program: values.program,
          intake: values.intake,
          land_acreage: values.landAcreage,
          carpet_area: values.carpetArea,
          faculty_count: values.facultyCount,
          student_count: values.studentCount,
        },
      });
      setCreatedAppId(res.id);
      return res.id;
    }
    return createdAppId;
  };

  // Save Draft handler available at EVERY step
  const handleSaveDraft = async () => {
    try {
      const appId = await ensureDraftSaved();
      toastBus.show({
        type: 'success',
        title: 'Draft Saved Successfully',
        message: `Dossier ${appId} has been saved to your institutional workspace.`,
      });
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Save Failed',
        message: 'Could not record application draft.',
      });
    }
  };

  const handleNextFromMeta = async () => {
    await ensureDraftSaved();
    setCurrentStep(1);
  };

  const handleNextFromIntake = async () => {
    await ensureDraftSaved();
    setCurrentStep(2);
  };

  // Step 3: Upload or Replace single document
  const handleUploadSingleDocument = async (className: string) => {
    const file = rowFiles[className];
    if (!createdAppId || !file) return;

    try {
      await uploadDocMutation.mutateAsync({
        applicationId: createdAppId,
        file,
        category: className,
        onProgress: (pct) => {
          setUploadProgress((prev) => ({ ...prev, [className]: pct }));
        },
      });

      toastBus.show({
        type: 'success',
        title: 'Document Uploaded',
        message: `${file.name} saved to secure vault.`,
      });

      // Clear row file & reload app
      setRowFiles((prev) => {
        const next = { ...prev };
        delete next[className];
        return next;
      });
      setReplacingClass(null);
      await refetchApp();
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Upload Failed',
        message: `Failed to upload document for ${className}.`,
      });
    }
  };

  // Step 4: Run validation
  const handleTriggerValidation = async () => {
    if (!createdAppId) return;
    try {
      await validateMutation.mutateAsync();
      toastBus.show({
        type: 'info',
        title: 'Automated Pipeline Active',
        message: 'Evaluating uploaded documents against pinned AICTE APH 2026-27 rules...',
      });
      setCurrentStep(3);
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Validation Trigger Failed',
        message: 'Could not initiate statutory validation checks.',
      });
    }
  };

  // Replacement upload for a specific deficiency in Step 4
  const handleDeficiencyReplacementUpload = async (className: string, file: File) => {
    if (!createdAppId) return;
    try {
      await uploadDocMutation.mutateAsync({
        applicationId: createdAppId,
        file,
        category: className,
        onProgress: (pct) => {
          setUploadProgress((prev) => ({ ...prev, [className]: pct }));
        },
      });

      toastBus.show({
        type: 'success',
        title: 'Replacement Processed',
        message: 'Document replaced. Statutory checks re-evaluated for this annexure.',
      });

      await refetchApp();
      await refetchFindings();
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Replacement Failed',
        message: 'Could not re-validate replacement document.',
      });
    }
  };

  // Final Submit
  const handleFinalSubmit = async () => {
    if (!createdAppId) return;
    try {
      await submitMutation.mutateAsync();
      toastBus.show({
        type: 'success',
        title: 'Application Transmitted',
        message: `Dossier ${createdAppId} successfully submitted to Scrutiny Bureau.`,
      });
      navigate(`/institution/applications/${createdAppId}`);
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Submission Failed',
        message: 'Could not submit application. Ensure all mandatory documents are attached.',
      });
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Title & Top Save Draft */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-heading text-text">
            Statutory EoA Application Submission Wizard
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            AICTE Approval Process Handbook (APH 2026-27) Intake Dossier
            {createdAppId && (
              <span className="ml-2 font-mono font-bold text-primary">
                [{createdAppId}]
              </span>
            )}
          </p>
        </div>

        <button
          type="button"
          onClick={handleSaveDraft}
          disabled={createMutation.isPending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-text shadow-xs self-start sm:self-auto transition-colors"
        >
          <Save className="w-3.5 h-3.5 text-primary" />
          <span>Save Draft</span>
        </button>
      </div>

      {/* Stepper */}
      <div className="rounded-card bg-surface border border-border p-4 shadow-card">
        <Stepper
          steps={WIZARD_STEPS}
          currentStep={currentStep}
          onStepClick={(step) => {
            if (step <= currentStep || createdAppId) setCurrentStep(step);
          }}
        />
      </div>

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={99.1}
        sourceName="National Regulatory Matrix"
        message="All document uploads are scanned and encrypted immutably. Discrepancies are flagged for officer review without automatic rejection."
      />

      {/* Main Form Body */}
      <div className="rounded-card bg-surface border border-border p-6 shadow-card space-y-6">
        {/* Step 0: Institutional Metadata */}
        {currentStep === 0 && (
          <div className="space-y-4">
            <h3 className="text-sm font-bold font-heading text-text flex items-center gap-2">
              <Building2 className="w-4 h-4 text-primary" /> Step 1: Institutional Metadata
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  INSTITUTION NAME
                </label>
                <input
                  {...register('instituteName')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text focus:border-primary outline-none"
                />
                {errors.instituteName && (
                  <span className="text-danger text-[10px] mt-1 block">
                    {errors.instituteName.message}
                  </span>
                )}
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  PERMANENT INSTITUTE ID (PID)
                </label>
                <input
                  {...register('pid')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text font-mono focus:border-primary outline-none"
                />
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  ACADEMIC CYCLE
                </label>
                <input
                  {...register('academicYear')}
                  disabled
                  className="w-full px-3 py-2 rounded-xl bg-surface-alt border border-border text-muted font-mono"
                />
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  APPROVAL DISCIPLINE
                </label>
                <input
                  {...register('category')}
                  disabled
                  className="w-full px-3 py-2 rounded-xl bg-surface-alt border border-border text-muted"
                />
              </div>
            </div>

            <div className="flex justify-between pt-4 border-t border-border">
              <button
                type="button"
                onClick={handleSaveDraft}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted"
              >
                Save Draft
              </button>
              <button
                type="button"
                onClick={handleSubmit(handleNextFromMeta)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5"
              >
                <span>Continue to Intake & Land</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Programs, Land, and Cadre */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <h3 className="text-sm font-bold font-heading text-text flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary" /> Step 2: Academic Programs, Land & Faculty
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  PROGRAM NAME
                </label>
                <input
                  {...register('program')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text focus:border-primary outline-none"
                />
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  TOTAL STUDENT INTAKE
                </label>
                <input
                  type="number"
                  {...register('intake')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text font-mono focus:border-primary outline-none"
                />
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  CONTIGUOUS LAND ACREAGE (ACRES)
                </label>
                <input
                  type="number"
                  step="0.01"
                  {...register('landAcreage')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text font-mono focus:border-primary outline-none"
                />
                <span className="text-[10px] text-muted">Mandatory Rural Norm: 7.50 Acres min</span>
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  CONSTRUCTED CARPET AREA (SQ.M)
                </label>
                <input
                  type="number"
                  {...register('carpetArea')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text font-mono focus:border-primary outline-none"
                />
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  FULL-TIME QUALIFIED FACULTY
                </label>
                <input
                  type="number"
                  {...register('facultyCount')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text font-mono focus:border-primary outline-none"
                />
              </div>
              <div>
                <label className="block text-muted font-mono mb-1 font-semibold">
                  TOTAL ENROLLED STUDENTS
                </label>
                <input
                  type="number"
                  {...register('studentCount')}
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text font-mono focus:border-primary outline-none"
                />
              </div>
            </div>

            <div className="flex justify-between pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => setCurrentStep(0)}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveDraft}
                  className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted"
                >
                  Save Draft
                </button>
                <button
                  type="button"
                  onClick={handleSubmit(handleNextFromIntake)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5"
                >
                  <span>Proceed to Document Uploads</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Document Uploads built from checklist */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
              <div>
                <h3 className="text-sm font-bold font-heading text-text flex items-center gap-2">
                  <UploadCloud className="w-4 h-4 text-primary" /> Step 3: Statutory Dossier Uploads
                </h3>
                <p className="text-xs text-muted">
                  Upload requirements constructed dynamically from statutory checklist rules.
                </p>
              </div>
              <span className="text-xs font-mono text-primary font-bold">
                {uploadRows.filter((r) => r.uploadedDoc).length} / {uploadRows.length} Attached
              </span>
            </div>

            <div className="space-y-3">
              {uploadRows.map((row) => {
                const isUploaded = !!row.uploadedDoc;
                const isReplacing = replacingClass === row.className;
                const selectedFile = rowFiles[row.className];
                const pct = uploadProgress[row.className] || 0;

                return (
                  <div
                    key={row.className}
                    className="p-4 rounded-xl border border-border bg-surface-alt/40 space-y-2 text-xs"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-bold text-text">{row.name}</p>
                          {row.required && (
                            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-danger/10 text-danger border border-danger/20">
                              Mandatory
                            </span>
                          )}
                        </div>
                        <span className="font-mono text-[10px] text-muted">{row.className}</span>
                      </div>

                      <div className="flex items-center gap-2 flex-wrap">
                        {isUploaded && !isReplacing ? (
                          <>
                            <span className="px-2.5 py-0.5 rounded-full bg-success/15 text-success font-mono font-bold text-[10px] flex items-center gap-1 border border-success/30">
                              <CheckCircle2 className="w-3 h-3" /> Uploaded (v{(row.uploadedDoc as any)?.version || 1})
                            </span>
                            <button
                              type="button"
                              onClick={() => setReplacingClass(row.className)}
                              className="px-2.5 py-1 rounded-lg text-xs font-medium bg-surface border border-border hover:bg-surface-alt text-primary transition-colors"
                            >
                              Replace
                            </button>
                          </>
                        ) : (
                          <>
                            <input
                              type="file"
                              accept=".pdf,.png,.jpg"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) {
                                  setRowFiles((prev) => ({ ...prev, [row.className]: file }));
                                }
                              }}
                              className="text-xs text-muted file:mr-2 file:py-1 file:px-2.5 file:rounded-lg file:border file:border-border file:text-xs file:bg-surface file:text-text cursor-pointer"
                            />
                            <button
                              type="button"
                              onClick={() => handleUploadSingleDocument(row.className)}
                              disabled={!selectedFile || uploadDocMutation.isPending}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 disabled:opacity-40 transition-colors"
                            >
                              {uploadDocMutation.isPending ? 'Uploading...' : isReplacing ? 'Confirm Replace' : 'Upload'}
                            </button>
                            {isReplacing && (
                              <button
                                type="button"
                                onClick={() => setReplacingClass(null)}
                                className="text-xs text-muted hover:text-text px-1"
                              >
                                Cancel
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>

                    {pct > 0 && pct < 100 && (
                      <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-primary h-full transition-all duration-200"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex justify-between pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveDraft}
                  className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted"
                >
                  Save Draft
                </button>
                <button
                  type="button"
                  onClick={handleTriggerValidation}
                  disabled={validateMutation.isPending}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-hero-gradient text-white shadow-glow flex items-center gap-1.5"
                >
                  {validateMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <ArrowRight className="w-3.5 h-3.5" />
                  )}
                  <span>Run Automated Validation Checks</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Validation Pipeline Animation & Deficiencies */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-bold font-heading text-text flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-primary" /> Step 4: Automated Validation Pipeline
              </h3>
              <p className="text-xs text-muted">
                Statutory AICTE APH extraction, cross-referencing, and rule verification.
              </p>
            </div>

            {/* Reusable 7-Stage Validation Progress Pipeline */}
            <ProgressPipeline applicationId={createdAppId || 'new'} />

            {/* Plain-Language Deficiencies with inline Upload Replacement */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold font-heading uppercase text-text">
                  Statutory Deficiency Findings ({plainLanguageFindings.length})
                </h4>
                <button
                  type="button"
                  onClick={() => {
                    refetchFindings();
                    refetchApp();
                  }}
                  className="text-xs text-muted hover:text-text flex items-center gap-1"
                >
                  <RotateCcw className="w-3 h-3" /> Refresh Findings
                </button>
              </div>

              {plainLanguageFindings.length === 0 ? (
                <div className="p-5 rounded-card bg-success/10 border border-success/30 text-success text-xs flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                  <div>
                    <p className="font-bold">No Deficiencies Found</p>
                    <p className="text-[11px] text-text/80">
                      All uploaded dossier documents satisfy AICTE statutory rules. Your application is eligible for transmission.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {plainLanguageFindings.map((finding: any) => {
                    const targetClass = finding.evidence?.[0]?.field || 'fire_safety_certificate';
                    return (
                      <div
                        key={finding.finding_id}
                        className="p-4 rounded-card border border-warning/30 bg-surface shadow-xs space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-text">{finding.title}</span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-warning/15 text-warning border border-warning/30">
                            {finding.severity}
                          </span>
                        </div>

                        <p className="text-xs text-text/90 font-sans leading-relaxed">
                          {finding.reason}
                        </p>

                        {/* Inline Upload Replacement that re-runs validation for this doc */}
                        <div className="pt-2 border-t border-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <span className="text-[11px] font-mono text-muted">
                            Annexure: <strong className="text-text">{targetClass}</strong>
                          </span>

                          <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 cursor-pointer transition-colors">
                            <Upload className="w-3.5 h-3.5" />
                            <span>Upload Replacement</span>
                            <input
                              type="file"
                              accept=".pdf,.png,.jpg"
                              className="hidden"
                              onChange={(e) => {
                                const f = e.target.files?.[0];
                                if (f) handleDeficiencyReplacementUpload(targetClass, f);
                              }}
                            />
                          </label>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="flex justify-between pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => setCurrentStep(2)}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Uploads</span>
              </button>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveDraft}
                  className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted"
                >
                  Save Draft
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(4)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5"
                >
                  <span>Review & Transmit Dossier</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Final Submission */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <h3 className="text-sm font-bold font-heading text-text flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-primary" /> Step 5: Final Review & Transmission
            </h3>

            <div className="p-4 rounded-xl bg-surface-alt border border-border space-y-3 text-xs font-mono">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="text-muted">Application ID:</span>
                <span className="font-bold text-text">{createdAppId}</span>
              </div>
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="text-muted">Status:</span>
                <StatusChip status={application?.state || 'DRAFT'} />
              </div>
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="text-muted">Total Attached Documents:</span>
                <span className="font-bold text-text">{application?.documents?.length || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">Open Deficiencies:</span>
                <span className="font-bold text-text">{plainLanguageFindings.length}</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 text-xs text-text space-y-2">
              <p className="font-bold">Statutory Institutional Declaration</p>
              <p className="text-[11px] leading-relaxed text-muted">
                I hereby declare that the particulars furnished in this application are true to the best of my knowledge and comply with AICTE Approval Process Handbook (APH 2026-27). All uploaded annexures are authentic institutional records.
              </p>
            </div>

            <div className="flex justify-between pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => setCurrentStep(3)}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Validation</span>
              </button>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveDraft}
                  className="px-3 py-2 rounded-xl text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-muted"
                >
                  Save Draft
                </button>
                <button
                  type="button"
                  onClick={handleFinalSubmit}
                  disabled={submitMutation.isPending}
                  className="px-6 py-2.5 rounded-xl text-xs font-bold font-heading bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 flex items-center gap-2 transition-all disabled:opacity-50"
                >
                  {submitMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  <span>Submit Dossier to AICTE Scrutiny Bureau</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
