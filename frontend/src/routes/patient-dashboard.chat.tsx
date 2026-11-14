import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  Send,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  BookOpen,
  Loader2,
  Bot,
  User,
  HelpCircle,
  FileText,
  Edit3,
  Heart,
  ShieldAlert,
  Users,
  Layers,
  ListChecks,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import { PatientShell } from "@/components/patient-shell";
import { Button } from "@/components/ui/button";
import { MotionCard } from "@/components/motion-card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { aiService, chatService, patientService, type AiSessionData } from "@/lib/api";
import {
  ACP_SECTIONS,
  getSectionStatus,
  getSectionProgress,
  getOverallProgress,
  nextAcpSection,
  type AcpSectionKey,
} from "@/lib/acp-workflow";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/patient-dashboard/chat")({ component: ChatPage });

/**
 * Maps Kannada display labels to their canonical English values.
 * Used when a patient clicks a Kannada option button so the canonical value
 * is submitted to the backend while the Kannada label is shown in the chat.
 */
const KN_TO_CANONICAL: Record<string, string> = {
  // Gender Q3
  "ಪುರುಷ": "Male", "ಮಹಿಳೆ": "Female", "ಇತರೆ": "Other",
  // Yes / No / Unsure (Q11-Q18, Q31, Q37, Q38)
  "ಹೌದು": "Yes", "ಇಲ್ಲ": "No", "ಖಚಿತವಿಲ್ಲ": "Unsure",
  // Goals of care Q19
  "ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಆರೈಕೆ": "Comfort-focused care",
  "ಜೀವನವನ್ನು ದೀರ್ಘಗೊಳಿಸುವ ಚಿಕಿತ್ಸೆ": "Life-prolonging treatment",
  "ಆರಾಮ ಮತ್ತು ಜೀವನವನ್ನು ದೀರ್ಘಗೊಳಿಸುವ ಚಿಕಿತ್ಸೆಯ ಸಮತೋಲನ": "A balance of comfort and life-prolonging treatment",
  // Preferred place of care Q20
  "ಮನೆ": "Home", "ಆಸ್ಪತ್ರೆ": "Hospital",
  "ಹಾಸ್ಪಿಸ್ ಅಥವಾ ಪ್ಯಾಲಿಯೇಟಿವ್ ಆರೈಕೆ ಕೇಂದ್ರ": "Hospice",
  "ಹಾಸ್ಪಿಸ್": "Hospice",
  "ಯಾವುದೇ ಆದ್ಯತೆ ಇಲ್ಲ": "No preference",
  "ಯಾವುದೇ ಆದ್ಯತೆಯಿಲ್ಲ": "No preference",
  // Level of medical intervention Q24
  "ಪೂರ್ಣ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ": "Full medical treatment",
  "ಸೀಮಿತ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ": "Limited medical treatment",
  "ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಚಿಕಿತ್ಸೆ": "Comfort-focused treatment",
  // Skip / none equivalents
  "ಬಿಟ್ಟುಬಿಡಿ": "Skip",
  "ನನ್ನ ವಿಳಾಸದಂತೆಯೇ": "Same as my address",
  "ಪ್ರಸ್ತುತ ವಿಳಾಸದಂತೆಯೇ": "Same as current address",
  "ಯಾವುದೇ ನಿರ್ದಿಷ್ಟ ಆಶಯವಿಲ್ಲ": "No specific wishes",
  "ಯಾವುದೇ ಆಶಯವಿಲ್ಲ": "No specific wishes",
  "ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಆಶಯಗಳಿಲ್ಲ": "No additional wishes",
  "ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಆಶಯವಿಲ್ಲ": "No additional wishes",
  // Government ID Type Q41
  "ಆಧಾರ್": "Aadhaar",
  "ಪಾಸ್‌ಪೋರ್ಟ್": "Passport",
  "ಡ್ರೈವಿಂಗ್ ಲೈಸೆನ್ಸ್": "Driving License",
  "ಮತದಾರರ ಗುರುತಿನ ಚೀಟಿ": "Voter ID",
  // Review / confirm Q44
  "ನನ್ನ ಯೋಜನೆಯನ್ನು ದೃಢೀಕರಿಸಿ": "Confirm & Complete ACP",
  "ದೃಢೀಕರಿಸಿ": "Confirm & Complete ACP",
  "ವೈಯಕ್ತಿಕ ವಿವರಗಳನ್ನು ತಿದ್ದು": "Edit Personal Details",
  "ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಗಳನ್ನು ತಿದ್ದು": "Edit Medical Treatments",
  "ಆರೈಕೆ ಆದ್ಯತೆಗಳನ್ನು ತಿದ್ದು": "Edit End-of-Life Wishes",
  "ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯನ್ನು ತಿದ್ದು": "Edit Healthcare Representative",
  "ದಾನದ ನಿರ್ಧಾರಗಳನ್ನು ತಿದ್ದು": "Edit Donation Preferences",
  "ಪರಿಶೀಲನೆಗೆ ಹಿಂತಿರುಗಿ": "Back to Review",
  "ಪ್ರಸ್ತುತ ಮೌಲ್ಯವನ್ನು ಇರಿಸಿ": "Keep Current Value",
};

interface MessageItem {
  id: string;
  from: "user" | "bot";
  text: string;
  status?: string;
  sources?: Array<{ source: string; category?: string; score?: number }> | null;
  timestamp?: string;
  isQuestion?: boolean;
  questionNumber?: number | null;
  options?: string[] | null;
}

const SECTION_ICONS: Record<AcpSectionKey, any> = {
  personal: User,
  medical: Heart,
  "end-of-life": ShieldAlert,
  proxy: Users,
  donation: Layers,
  review: ListChecks,
};

function ChatPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatScrollContainerRef = useRef<HTMLDivElement>(null);

  const [draft, setDraft] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState<"en" | "kn">("en");
  const [activeSession, setActiveSession] = useState<AiSessionData | null>(null);
  const [currentQuestionData, setCurrentQuestionData] = useState<{
    question_number: number | null;
    question: string;
    options: string[] | null;
  } | null>(null);
  const [sessionLostError, setSessionLostError] = useState(false);
  const [showRestartDialog, setShowRestartDialog] = useState(false);
  const [validationError, setValidationError] = useState<{ questionNumber: number | null; message: string } | null>(null);
  const [missingRequiredFields, setMissingRequiredFields] = useState<string[]>([]);
  const sendLockedRef = useRef(false);
  const editHandledRef = useRef<string | null>(null);

  const sectionForMissingField = (field: string): AcpSectionKey => {
    const normalized = field.toLowerCase();
    if (/representative|dhr|ಪ್ರತಿನಿಧಿ/.test(normalized)) return "proxy";
    if (/organ|body donation|ಅಂಗದಾನ|ದೇಹದಾನ/.test(normalized)) return "donation";
    if (/goal|care|wishes|intervention|value|place|ಆರೈಕೆ|ಆಶಯ|ಮೌಲ್ಯ/.test(normalized)) return "end-of-life";
    if (/medical|treatment|cpr|dialysis|ventilator|nutrition|hydration|chemotherapy|radiotherapy|surgery|condition|allerg|medication|hospital|ಚಿಕಿತ್ಸೆ|ಕಾಯಿಲೆ|ಅಲರ್ಜಿ/.test(normalized)) return "medical";
    return "personal";
  };

  // 1. Fetch patient profile
  const { data: profile } = useQuery({
    queryKey: ["patientProfile"],
    queryFn: patientService.getProfile,
  });
  const patientId = profile?.patient_id;

  // 2. Fetch ACP clinical preferences
  const { data: acpData } = useQuery({
    queryKey: ["patientAcp", patientId],
    queryFn: () => patientService.getACP(patientId!),
    enabled: !!patientId,
  });

  // 3. Fetch DHR representatives
  const { data: dhrData = [] } = useQuery({
    queryKey: ["patientDhrs", patientId],
    queryFn: () => patientService.getDHRs(patientId!),
    enabled: !!patientId,
  });

  // Initialize language from profile if available
  useEffect(() => {
    if (profile?.preferred_language) {
      const isKn = profile.preferred_language.toLowerCase().includes("kannada");
      setSelectedLanguage(isKn ? "kn" : "en");
    }
  }, [profile?.preferred_language]);

  // 4. Fetch active AI session from backend
  const { data: activeSessionResp } = useQuery({
    queryKey: ["activeAiSession", patientId],
    queryFn: aiService.getActiveSession,
    enabled: !!patientId,
  });

  useEffect(() => {
    if (activeSessionResp?.session) {
      setActiveSession(activeSessionResp.session);
      if (activeSessionResp.session.language === "kn" || activeSessionResp.session.language === "en") {
        setSelectedLanguage(activeSessionResp.session.language as "en" | "kn");
      }
      if (activeSessionResp.session.current_question) {
        setCurrentQuestionData({
          question_number: activeSessionResp.session.current_question,
          question: activeSessionResp.session.question || `Question ${activeSessionResp.session.current_question}`,
          options: activeSessionResp.session.options || null,
        });
      }
    }
  }, [activeSessionResp]);

  // 5. Fetch chat history for this patient
  const { data: dbHistory = [], isLoading: isLoadingHistory } = useQuery({
    queryKey: ["chatHistory", patientId],
    queryFn: () => chatService.getHistory(patientId),
    enabled: !!patientId,
  });

  // Local message state allows instant UI updates alongside server persistence
  const [localMessages, setLocalMessages] = useState<MessageItem[]>([]);

  // Sync historical messages when dbHistory loads or changes
  useEffect(() => {
    if (!activeSession?.session_id) return;
    const sessionHistory = dbHistory.filter((item: any) => item.session_id === activeSession.session_id);

    if (sessionHistory.length > 0) {
      const historical: MessageItem[] = [];
      sessionHistory.forEach((item: any) => {
        // 1. Complete Question as chatbot message immediately before patient's answer
        if (item.question) {
          historical.push({
            id: `${item.id}-q`,
            from: "bot",
            text: item.question,
            isQuestion: true,
            questionNumber: item.question_number ?? null,
            options: item.options ?? null,
            timestamp: item.created_at,
          });
        }
        // 2. Patient's answer directly below that question
        historical.push({
          id: `${item.id}-user`,
          from: "user",
          text: item.user_message,
          questionNumber: item.question_number ?? null,
          timestamp: item.created_at,
        });
        // 3. Chatbot confirmation or educational explanation
        historical.push({
          id: `${item.id}-bot`,
          from: "bot",
          text: item.bot_response,
          status: item.status,
          questionNumber: item.question_number ?? null,
          timestamp: item.created_at,
        });
      });

      // 4. If questionnaire is in-progress, append active question at the end if not already in historical
      if (
        currentQuestionData?.question &&
        !activeSession?.is_completed &&
        !historical.some((message) => message.isQuestion && Number(message.questionNumber) === Number(currentQuestionData.question_number))
      ) {
        historical.push({
          id: `active-q-${currentQuestionData.question_number ?? Date.now()}`,
          from: "bot",
          text: currentQuestionData.question,
          isQuestion: true,
          questionNumber: currentQuestionData.question_number,
          options: currentQuestionData.options,
        });
      }

      setLocalMessages(historical);
    } else if (sessionHistory.length === 0 && currentQuestionData?.question && !activeSession?.is_completed) {
      setLocalMessages((prev) => {
        // Prevent duplication if the current question is already shown in prev
        if (prev.some((m) => m.isQuestion && Number(m.questionNumber) === Number(currentQuestionData.question_number))) {
          return prev;
        }
        const welcomeText =
          selectedLanguage === "kn"
            ? "ನಮಸ್ಕಾರ. ನಿಮ್ಮ ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯನ್ನು (Advance Care Planning) ಸಂಪೂರ್ಣವಾಗಿ ಸಿದ್ಧಪಡಿಸಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ."
            : "Hello. I will help guide you through recording your complete Advance Care Planning (ACP) preferences.";
        return [
          {
            id: `welcome-${Date.now()}`,
            from: "bot",
            text: welcomeText,
          },
          {
            id: `initial-q-${currentQuestionData.question_number ?? Date.now()}`,
            from: "bot",
            text: currentQuestionData.question,
            isQuestion: true,
            questionNumber: currentQuestionData.question_number,
            options: currentQuestionData.options,
          },
        ];
      });
    }
  }, [dbHistory, currentQuestionData, activeSession?.is_completed, activeSession?.session_id, selectedLanguage]);

  // Keep the active question at the end of conversation synchronized with language / state
  useEffect(() => {
    if (!currentQuestionData?.question || activeSession?.is_completed) return;
    setValidationError((current) => (Number(current?.questionNumber) === Number(currentQuestionData.question_number) ? current : null));
    setLocalMessages((prev) => {
      if (prev.length === 0) return prev;
      const targetQNum = Number(currentQuestionData.question_number);

      // Check if this question is already rendered
      const activeIndex = prev.findIndex((message) => message.isQuestion && Number(message.questionNumber) === targetQNum);
      if (activeIndex >= 0) {
        return prev.map((message, index) =>
          index === activeIndex
            ? { ...message, text: currentQuestionData.question, options: currentQuestionData.options, questionNumber: currentQuestionData.question_number }
            : message
        );
      }

      // If the last message is already an unanswered question, update it in place to avoid duplicates
      const lastIndex = prev.length - 1;
      const lastMsg = prev[lastIndex];
      if (lastMsg && lastMsg.isQuestion) {
        return prev.map((message, index) =>
          index === lastIndex
            ? { ...message, text: currentQuestionData.question, options: currentQuestionData.options, questionNumber: currentQuestionData.question_number }
            : message
        );
      }

      return [
        ...prev,
        {
          id: `active-q-${currentQuestionData.question_number ?? Date.now()}`,
          from: "bot",
          text: currentQuestionData.question,
          isQuestion: true,
          questionNumber: currentQuestionData.question_number,
          options: currentQuestionData.options,
        },
      ];
    });
  }, [currentQuestionData, activeSession?.is_completed]);


  // Automatically scroll only the chat container to the latest message without moving the entire page
  useEffect(() => {
    if (chatScrollContainerRef.current) {
      chatScrollContainerRef.current.scrollTo({
        top: chatScrollContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [localMessages]);

  // Mutation to create or restart session
  const startSessionMutation = useMutation({
    mutationFn: (lang: "en" | "kn") => aiService.createSession(lang),
    onSuccess: (data) => {
      setDraft("");
      setValidationError(null);
      sendLockedRef.current = false;
      setMissingRequiredFields([]);
      setActiveSession(data);
      setSessionLostError(false);
      const qNum = data.question_number ?? data.current_question ?? 1;
      const qText =
        data.question ||
        (data.language === "kn" ? "ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರು ಏನು?" : "What is your full name?");
      const qOpts = data.options || null;

      setCurrentQuestionData({
        question_number: qNum,
        question: qText,
        options: qOpts,
      });

      const welcomeText =
        data.language === "kn"
          ? "ನಮಸ್ಕಾರ. ನಿಮ್ಮ ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯನ್ನು (Advance Care Planning) ಸಂಪೂರ್ಣವಾಗಿ ಸಿದ್ಧಪಡಿಸಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ."
          : "Hello. I will help guide you through recording your complete Advance Care Planning (ACP) preferences.";

      setLocalMessages([
        {
          id: `welcome-${Date.now()}`,
          from: "bot",
          text: welcomeText,
        },
        {
          id: `start-q-${qNum}-${Date.now()}`,
          from: "bot",
          text: qText,
          isQuestion: true,
          questionNumber: qNum,
          options: qOpts,
        },
      ]);

      queryClient.invalidateQueries({ queryKey: ["activeAiSession", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAcp", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientProfile"] });
      queryClient.invalidateQueries({ queryKey: ["patientDhrs", patientId] });

      toast.success(
        data.language === "kn"
          ? "ಕನ್ನಡದಲ್ಲಿ ಪ್ರಶ್ನಾವಳಿ ಪ್ರಾರಂಭವಾಗಿದೆ."
          : "Questionnaire session started in English."
      );
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to start AI session.");
    },
  });

  // Mutation to restart the questionnaire – resets ACP data and starts from Q1
  const restartSessionMutation = useMutation({
    mutationFn: (lang: "en" | "kn") => aiService.restartSession(lang),
    onSuccess: (data) => {
      setDraft("");
      setValidationError(null);
      sendLockedRef.current = false;
      setMissingRequiredFields([]);
      setActiveSession(data);
      setSessionLostError(false);
      const qNum = data.question_number ?? data.current_question ?? 1;
      const qText =
        data.question ||
        (data.language === "kn" ? "ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರು ಏನು?" : "What is your full name?");
      const qOpts = data.options || null;

      setCurrentQuestionData({
        question_number: qNum,
        question: qText,
        options: qOpts,
      });

      const restartText =
        data.language === "kn"
          ? "ನಿಮ್ಮ ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆ ಮರುಪ್ರಾರಂಭವಾಗಿದೆ. ನಾವು ಮೊದಲ ಪ್ರಶ್ನೆಯಿಂದ ಮತ್ತೆ ಪ್ರಾರಂಭಿಸುತ್ತೇವೆ."
          : "Your Advance Care Planning questionnaire has been restarted. We will begin again from Question 1.";

      setLocalMessages([
        {
          id: `restart-${Date.now()}`,
          from: "bot",
          text: restartText,
        },
        {
          id: `start-q-${qNum}-${Date.now()}`,
          from: "bot",
          text: qText,
          isQuestion: true,
          questionNumber: qNum,
          options: qOpts,
        },
      ]);

      queryClient.invalidateQueries({ queryKey: ["activeAiSession", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAcp", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientProfile"] });
      queryClient.invalidateQueries({ queryKey: ["patientDhrs", patientId] });
      queryClient.invalidateQueries({ queryKey: ["chatHistory", patientId] });

      toast.success(
        data.language === "kn"
          ? "ಪ್ರಶ್ನಾವಳಿ ಮರುಪ್ರಾರಂಭವಾಗಿದೆ. ಪ್ರಗತಿ 0% ಗೆ ಮರುಹೊಂದಿಸಲಾಗಿದೆ."
          : "Questionnaire restarted. Progress reset to 0%."
      );
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to restart session. Please try again.");
    },
  });

  // Mutation to seamlessly switch language without losing answers
  const updateLanguageMutation = useMutation({
    mutationFn: async (lang: "en" | "kn") => {
      setSelectedLanguage(lang);
      if (activeSession?.session_id) {
        return aiService.updateSessionLanguage(activeSession.session_id, lang);
      }
      return null;
    },
    onSuccess: (updated) => {
      if (updated) {
        setActiveSession((prev) => (prev ? { ...prev, ...updated } : updated));
        if (updated.question) {
          setCurrentQuestionData({
            question_number: updated.current_question ?? null,
            question: updated.question,
            options: updated.options ?? null,
          });
        }
      }
      queryClient.invalidateQueries({ queryKey: ["activeAiSession", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientProfile"] });
      toast.success(
        selectedLanguage === "kn"
          ? "ಭಾಷೆಯನ್ನು ಕನ್ನಡಕ್ಕೆ ಬದಲಾಯಿಸಲಾಗಿದೆ."
          : "Language updated to English."
      );
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to switch language.");
    },
  });

  const handleLanguageToggle = (lang: "en" | "kn") => {
    if (selectedLanguage === lang) return;
    updateLanguageMutation.mutate(lang);
  };

  // Mutation to send message
  const sendMessageMutation = useMutation({
    mutationFn: async ({ text }: { text: string; display: string }) => {
      if (!activeSession?.session_id) {
        throw new Error("No active session found. Please start a session first.");
      }
      return aiService.sendMessage(
        activeSession.session_id,
        text,
        currentQuestionData?.question_number
      );
    },
    onSuccess: (res, { display }) => {
      const sentMessage = display;
      const isMissingNotice = /cannot complete acp/i.test(res.message) || /missing:/i.test(res.message);
      if (isMissingNotice) {
        const missingMatch = res.message.match(/missing:\s*(.+?)(?:\.|$)/i)?.[1];
        const fields = missingMatch ? missingMatch.split(/,\s*/).filter(Boolean) : [];
        if (fields.length > 0) {
          setMissingRequiredFields(fields);
        }
        const missingSections = fields.map((f: string) => sectionForMissingField(f));
        const firstIncompleteFromMissing = ACP_SECTIONS.find((s) => missingSections.includes(s.key))?.key;
        const targetSec =
          firstIncompleteFromMissing ||
          (nextAcpSection(profile, acpData, dhrData) !== "review"
            ? nextAcpSection(profile, acpData, dhrData)
            : "personal");

        window.sessionStorage.setItem("acpReturnToReview", "1");
        toast.info(
          selectedLanguage === "kn"
            ? "ಬಾಕಿ ಇರುವ ವಿವರಗಳನ್ನು ನಮೂದಿಸಲು ACP ಫಾರ್ಮ್ ತೆರೆಯಲಾಗುತ್ತಿದೆ…"
            : "Opening form to complete remaining required entries: " +
                (fields.length > 0 ? fields.join(", ") : "required fields")
        );
        navigate({
          to: "/patient-dashboard/acp/$section",
          params: { section: targetSec },
        });
        return;
      }

      if (res.status === "invalid") {
        setValidationError({ questionNumber: res.question_number ?? currentQuestionData?.question_number ?? null, message: res.message });
      } else {
        setDraft("");
        setValidationError(null);
      }

      const qNum = res.question_number ?? currentQuestionData?.question_number ?? null;
      const answeredQText = res.answered_question?.question ?? currentQuestionData?.question;
      const answeredQOpts = res.answered_question?.options ?? currentQuestionData?.options;

      setLocalMessages((prev) => {
        const updated = [...prev];

        // 1. Ensure the answered question is visible right before the user's answer
        const lastMsg = updated[updated.length - 1];
        if (!lastMsg || !lastMsg.isQuestion || Number(lastMsg.questionNumber) !== Number(qNum)) {
          if (answeredQText) {
            updated.push({
              id: `q-${qNum}-${Date.now()}`,
              from: "bot",
              text: answeredQText,
              isQuestion: true,
              questionNumber: qNum,
              options: answeredQOpts,
            });
          }
        }

        // 2. Patient's answer directly below that question
        updated.push({
          id: `user-${Date.now()}`,
          from: "user",
          text: sentMessage,
          questionNumber: qNum,
        });

        // 3. Chatbot confirmation or educational explanation
        updated.push({
          id: `bot-${Date.now()}`,
          from: "bot",
          text: res.message,
          status: res.status,
          sources: res.sources,
          questionNumber: qNum,
        });

        // 4. Next chatbot question in chronological order (or active question awaiting retry if invalid)
        if (res.status !== "completed") {
          const nextQ = res.next_question || (res.status === "invalid" && answeredQText ? { question_number: qNum ?? 1, question: answeredQText, options: answeredQOpts } : null);
          if (nextQ && nextQ.question) {
            updated.push({
              id: `q-${nextQ.question_number}-${Date.now()}`,
              from: "bot",
              text: nextQ.question,
              isQuestion: true,
              questionNumber: nextQ.question_number,
              options: nextQ.options,
            });
          }
        }

        return updated;
      });

      if (res.status === "completed") {
        setActiveSession((prev) => (prev ? { ...prev, is_completed: true, current_question: 44 } : null));
        setCurrentQuestionData(null);
        toast.success(
          selectedLanguage === "kn"
            ? "ಪ್ರಶ್ನಾವಳಿ ಪೂರ್ಣಗೊಂಡಿದೆ! ನಿಮ್ಮ ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯ ಪರಿಶೀಲನೆ ತೆರೆಯಲಾಗುತ್ತಿದೆ…"
            : "Questionnaire completed! Opening your Advance Care Planning review…"
        );
        const targetSection = (res.redirect_section as AcpSectionKey) || "review";
        setTimeout(() => {
          navigate({
            to: "/patient-dashboard/acp/$section",
            params: { section: targetSection || "review" },
          });
        }, 1200);
      } else if (res.next_question) {
        const nextQ = res.next_question;
        setActiveSession((prev) => (prev ? { ...prev, is_completed: false, current_question: nextQ.question_number } : null));
        setCurrentQuestionData({
          question_number: nextQ.question_number,
          question: nextQ.question,
          options: nextQ.options,
        });
      }

      // Live invalidation updates the 6-section progress bar instantly!
      queryClient.invalidateQueries({ queryKey: ["chatHistory", patientId] });
      queryClient.invalidateQueries({ queryKey: ["activeAiSession", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAcp", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientProfile"] });
      queryClient.invalidateQueries({ queryKey: ["patientDhrs", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAuditLogs", patientId] });
      queryClient.invalidateQueries({ queryKey: ["aiDoctorDashboard", patientId] });
    },
    onError: (err: any) => {
      if (err?.status === 404) {
        setSessionLostError(true);
        toast.error("Session expired or cleared. Please start a new session.");
      } else {
        toast.error(err?.message || "Failed to send message.");
      }
    },
    onSettled: () => { sendLockedRef.current = false; },
  });

  // Handle edit requests passed via ?editQuestion=X from the review cards
  useEffect(() => {
    if (!activeSession?.session_id || sendMessageMutation.isPending) return;
    const urlParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
    const editQ = urlParams?.get("editQuestion");
    if (!editQ || editHandledRef.current === editQ) return;

    editHandledRef.current = editQ;
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, "", cleanUrl);

    const qNum = parseInt(editQ, 10);
    let editMsg = "";
    if (qNum === 1 || (qNum >= 1 && qNum <= 6)) {
      editMsg = selectedLanguage === "kn" ? "ವೈಯಕ್ತಿಕ ವಿವರಗಳನ್ನು ತಿದ್ದು" : "Edit personal details";
    } else if (qNum === 7 || (qNum >= 7 && qNum <= 10)) {
      editMsg = selectedLanguage === "kn" ? "ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಗಳನ್ನು ತಿದ್ದು" : "Edit medical background";
    } else if (qNum === 11 || (qNum >= 11 && qNum <= 18)) {
      editMsg = selectedLanguage === "kn" ? "ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಗಳನ್ನು ತಿದ್ದು" : "Edit medical treatments";
    } else if (qNum === 19 || (qNum >= 19 && qNum <= 25)) {
      editMsg = selectedLanguage === "kn" ? "ಆರೈಕೆ ಆದ್ಯತೆಗಳನ್ನು ತಿದ್ದು" : "Edit care preferences";
    } else if (qNum === 26 || (qNum >= 26 && qNum <= 36)) {
      editMsg = selectedLanguage === "kn" ? "ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯನ್ನು ತಿದ್ದು" : "Edit healthcare representative";
    } else if (qNum >= 37) {
      editMsg = selectedLanguage === "kn" ? "ದಾನದ ನಿರ್ಧಾರಗಳನ್ನು ತಿದ್ದು" : "Edit donation preferences";
    }

    if (editMsg) {
      // For Kannada sessions, map the edit command to canonical English so the backend recognises it.
      const canonicalEditMsg = selectedLanguage === "kn" ? (KN_TO_CANONICAL[editMsg] ?? editMsg) : editMsg;
      sendMessageMutation.mutate({ text: canonicalEditMsg, display: editMsg });
    }
  }, [activeSession?.session_id, selectedLanguage, sendMessageMutation]);

  // Mutation to explicitly confirm review and complete the ACP
  const confirmReviewMutation = useMutation({
    mutationFn: async () => {
      return aiService.confirmReview(activeSession?.session_id);
    },
    onSuccess: (res) => {
      setActiveSession((prev) => (prev ? { ...prev, is_completed: true, current_question: 44 } : null));
      if (res.next_question) {
        const nextQ = res.next_question;
        setCurrentQuestionData({
          question_number: nextQ.question_number,
          question: nextQ.question,
          options: nextQ.options,
        });
      }
      setLocalMessages((prev) => [
        ...prev,
        {
          id: `bot-confirmed-${Date.now()}`,
          from: "bot",
          text: res.message,
          status: "completed",
        },
      ]);
      queryClient.invalidateQueries({ queryKey: ["patientAcp", patientId] });
      queryClient.invalidateQueries({ queryKey: ["activeAiSession", patientId] });
      queryClient.invalidateQueries({ queryKey: ["chatHistory", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAuditLogs", patientId] });
      queryClient.invalidateQueries({ queryKey: ["aiDoctorDashboard", patientId] });
      toast.success(
        selectedLanguage === "kn"
          ? "ನಿಮ್ಮ ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿದೆ!"
          : "Advance Care Plan successfully confirmed and finalized!"
      );
      setTimeout(() => {
        navigate({
          to: "/patient-dashboard/acp/$section",
          params: { section: "review" },
        });
      }, 1200);
    },
    onError: (err: any) => {
      const message = err?.message || "Failed to confirm review.";
      const missing = message.match(/missing:\s*(.+?)(?:\.$|$)/i)?.[1];
      if (missing) {
        const fields = missing.split(/,\s*/).filter(Boolean);
        setMissingRequiredFields(fields);
        const missingSections = fields.map((f: string) => sectionForMissingField(f));
        const firstIncompleteFromMissing = ACP_SECTIONS.find((s) => missingSections.includes(s.key))?.key;
        const targetSec =
          firstIncompleteFromMissing ||
          (nextAcpSection(profile, acpData, dhrData) !== "review"
            ? nextAcpSection(profile, acpData, dhrData)
            : "personal");

        window.sessionStorage.setItem("acpReturnToReview", "1");
        navigate({
          to: "/patient-dashboard/acp/$section",
          params: { section: targetSec },
        });
        toast.info(
          selectedLanguage === "kn"
            ? "ಬಾಕಿ ಇರುವ ವಿವರಗಳನ್ನು ನಮೂದಿಸಲು ACP ಫಾರ್ಮ್ ತೆರೆಯಲಾಗಿದೆ."
            : "The ACP form is open for the remaining required details."
        );
        return;
      }
      toast.error(message);
    },
  });

  const handleSend = (textToSend?: string) => {
    const text = (textToSend ?? draft).trim();
    if (!text || !activeSession?.session_id || sendMessageMutation.isPending || sendLockedRef.current) return;

    const isConfirm =
      /confirm\s*&\s*complete/i.test(text) ||
      /ನನ್ನ ಯೋಜನೆಯನ್ನು ದೃಢೀಕರಿಸಿ/.test(text) ||
      text.toLowerCase() === "confirm";

    if (isConfirm) {
      const pending = nextAcpSection(profile, acpData, dhrData);
      if (pending !== "review") {
        window.sessionStorage.setItem("acpReturnToReview", "1");
        toast.info(
          selectedLanguage === "kn"
            ? "ಬಾಕಿ ಇರುವ ವಿವರಗಳನ್ನು ನಮೂದಿಸಲು ACP ಫಾರ್ಮ್ ತೆರೆಯಲಾಗುತ್ತಿದೆ…"
            : "Opening form to complete remaining required entries..."
        );
        navigate({
          to: "/patient-dashboard/acp/$section",
          params: { section: pending },
        });
        return;
      }
    }

    const canonicalText = KN_TO_CANONICAL[text] ?? text;
    sendLockedRef.current = true;
    sendMessageMutation.mutate({ text: canonicalText, display: text });
  };

  /**
   * Handle a predefined option button click.
   * For Kannada sessions, maps the display label to its canonical English value
   * before sending to the backend, while showing the original label in the chat.
   */
  const handleSendOption = (displayLabel: string) => {
    if (!displayLabel || !activeSession?.session_id || sendMessageMutation.isPending || sendLockedRef.current) return;
    const canonical = selectedLanguage === "kn" ? (KN_TO_CANONICAL[displayLabel] ?? displayLabel) : displayLabel;
    sendLockedRef.current = true;
    sendMessageMutation.mutate({ text: canonical, display: displayLabel });
  };

  const handleStart = () => {
    startSessionMutation.mutate(selectedLanguage);
  };

  const handleRestartClick = () => {
    if (activeSession) {
      setShowRestartDialog(true);
    } else {
      startSessionMutation.mutate(selectedLanguage);
    }
  };

  // Calculate live 6-section metrics
  const isPlanCompleted = Boolean(acpData?.is_completed || activeSession?.is_completed);
  const overallProgress = getOverallProgress(profile, acpData, dhrData);

  const sectionProgressItems = ACP_SECTIONS.map((sec) => {
    const status = getSectionStatus(sec.key, profile, acpData, dhrData);
    const progress = getSectionProgress(sec.key, profile, acpData, dhrData);
    const IconComponent = SECTION_ICONS[sec.key];
    return {
      ...sec,
      status,
      progress,
      IconComponent,
    };
  });

  const isReviewStep =
    currentQuestionData?.question_number === 36 ||
    Boolean(
      currentQuestionData?.options?.includes("Confirm & Complete ACP") ||
      currentQuestionData?.options?.includes("ನನ್ನ ಯೋಜನೆಯನ್ನು ದೃಢೀಕರಿಸಿ")
    );
  const activeQuestionMessageId = [...localMessages].reverse().find((message) =>
    message.isQuestion && Number(message.questionNumber) === Number(currentQuestionData?.question_number)
  )?.id;

  return (
    <PatientShell>
      {/* Header */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Advance Care Planning Assistant
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Complete all six ACP sections through this bilingual conversational assistant.
          </p>
        </div>

        {/* Language selector & Start button */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center rounded-xl border border-border bg-surface p-1 shadow-2xs">
            <Button
              type="button"
              size="sm"
              variant={selectedLanguage === "en" ? "default" : "ghost"}
              className="h-8 rounded-lg text-xs font-medium"
              onClick={() => handleLanguageToggle("en")}
              disabled={updateLanguageMutation.isPending || sendMessageMutation.isPending}
            >
              English
            </Button>
            <Button
              type="button"
              size="sm"
              variant={selectedLanguage === "kn" ? "default" : "ghost"}
              className="h-8 rounded-lg text-xs font-medium"
              onClick={() => handleLanguageToggle("kn")}
              disabled={updateLanguageMutation.isPending || sendMessageMutation.isPending}
            >
              ಕನ್ನಡ (Kannada)
            </Button>
          </div>

          {typeof window !== "undefined" && window.sessionStorage.getItem("acpReturnToReview") === "1" && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 rounded-xl font-medium border-primary/40 text-primary hover:bg-primary/10"
              onClick={() => {
                window.sessionStorage.removeItem("acpReturnToReview");
                navigate({ to: "/patient-dashboard/acp/$section", params: { section: "review" } });
              }}
            >
              Return to ACP Review
            </Button>
          )}

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRestartClick}
            disabled={startSessionMutation.isPending}
            className="h-9 rounded-xl font-medium"
          >
            {startSessionMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="mr-2 h-4 w-4" />
            )}
            {activeSession ? "Restart Session" : "Start Questionnaire"}
          </Button>
        </div>
      </header>

      {/* 6-Section Live ACP Progress Tracker */}
      <MotionCard className="mt-4 p-4 sm:p-5">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Six-Section Advance Care Plan Progress
              </span>
            </div>
            <div className="flex items-center gap-2">
              {isPlanCompleted ? (
                <Badge className="border-success/30 bg-success/10 text-success">
                  <CheckCircle2 className="mr-1 h-3 w-3" /> 100% Completed
                </Badge>
              ) : (
                <span className="text-xs font-bold text-foreground">
                  {overallProgress}% Total Completion
                </span>
              )}
            </div>
          </div>

          <Progress value={isPlanCompleted ? 100 : overallProgress} className="h-2 rounded-full" />

          {/* Section Pills Grid */}
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            {sectionProgressItems.map((item) => {
              const Icon = item.IconComponent;
              const isCompleted = item.status === "completed";
              const isInProgress = item.status === "in_progress";

              return (
                <div
                  key={item.key}
                  className={cn(
                    "flex flex-col justify-between rounded-xl border p-2.5 transition",
                    isCompleted
                      ? "border-success/40 bg-success/5"
                      : isInProgress
                        ? "border-primary/40 bg-primary/5"
                        : "border-border/70 bg-surface/50 opacity-70"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div
                      className={cn(
                        "grid h-6 w-6 place-items-center rounded-lg text-xs",
                        isCompleted
                          ? "bg-success/20 text-success"
                          : isInProgress
                            ? "bg-primary/20 text-primary"
                            : "bg-muted text-muted-foreground"
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <span
                      className={cn(
                        "text-[10px] font-bold",
                        isCompleted
                          ? "text-success"
                          : isInProgress
                            ? "text-primary"
                            : "text-muted-foreground"
                      )}
                    >
                      {item.progress}%
                    </span>
                  </div>

                  <p className="mt-2 line-clamp-1 text-xs font-semibold text-foreground">
                    {item.title}
                  </p>

                  <div className="mt-1 flex items-center justify-between text-[10px]">
                    <span
                      className={cn(
                        "font-medium capitalize",
                        isCompleted
                          ? "text-success"
                          : isInProgress
                            ? "text-primary"
                            : "text-muted-foreground"
                      )}
                    >
                      {item.status.replace("_", " ")}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </MotionCard>

      {/* Completion Banner */}
      {isPlanCompleted && (
        <MotionCard className="mt-4 border-success/30 bg-success/5 p-4 sm:p-5">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-success/20 text-success">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <div>
                  <p className="font-bold text-foreground">
                    {selectedLanguage === "kn"
                      ? "ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿದೆ"
                      : "Advance Care Plan Finalized & Recorded"}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {selectedLanguage === "kn"
                      ? "ನಿಮ್ಮ ಎಲ್ಲಾ ಆರು ವಿಭಾಗಗಳ ನಿರ್ಧಾರಗಳು ಸುರಕ್ಷಿತವಾಗಿ ದಾಖಲಾಗಿವೆ. ನೀವು ಈಗ ಸಾಕ್ಷಿಗಳನ್ನು ನೇಮಿಸಿ ಅಧಿಕೃತ AMD ದಾಖಲೆಯನ್ನು ಮುದ್ರಿಸಬಹುದು."
                      : "Your choices across all six sections are committed. You can now appoint your two witnesses and generate your official Advance Medical Directive (AMD) document."}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  to="/patient-dashboard/documents"
                  className="inline-flex h-10 shrink-0 items-center justify-center rounded-xl bg-success px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-success/90"
                >
                  <FileText className="mr-2 h-4 w-4" />
                  {selectedLanguage === "kn"
                    ? "ಸಾಕ್ಷಿಗಳನ್ನು ನೇಮಿಸಿ & AMD ಮುದ್ರಿಸಿ"
                    : "Appoint Witnesses & Generate AMD"}
                </Link>
              </div>
            </div>

            {/* Quick Edit Choices for Completed Plan */}
            <div className="border-t border-success/20 pt-3">
              <p className="mb-2 text-xs font-semibold text-muted-foreground">
                {selectedLanguage === "kn"
                  ? "ನಿಮ್ಮ ನಿರ್ಧಾರಗಳಲ್ಲಿ ಬದಲಾವಣೆ ಮಾಡಬೇಕೇ? ಯಾವುದೇ ವಿಭಾಗವನ್ನು ತಕ್ಷಣವೇ ತಿದ್ದುಪಡಿ ಮಾಡಲು ಕೆಳಗಿನ ಆಯ್ಕೆಯನ್ನು ಆರಿಸಿ:"
                  : "Need to adjust any preference in your finalized plan? Select a section to modify without restarting:"}
              </p>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: selectedLanguage === "kn" ? "ವೈಯಕ್ತಿಕ ವಿವರಗಳನ್ನು ತಿದ್ದು" : "Edit Personal Details", cmd: "Edit Personal Details" },
                  { label: selectedLanguage === "kn" ? "ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯನ್ನು ತಿದ್ದು" : "Edit Healthcare Representative", cmd: "Edit Healthcare Representative" },
                  { label: selectedLanguage === "kn" ? "ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಗಳನ್ನು ತಿದ್ದು" : "Edit Medical Treatments", cmd: "Edit Medical Treatments" },
                  { label: selectedLanguage === "kn" ? "ಕೀಮೋಥೆರಪಿಯನ್ನು ತಿದ್ದು" : "Edit Chemotherapy", cmd: "Edit Chemotherapy" },
                  { label: selectedLanguage === "kn" ? "ರೇಡಿಯೋಥೆರಪಿಯನ್ನು ತಿದ್ದು" : "Edit Radiotherapy", cmd: "Edit Radiotherapy" },
                  { label: selectedLanguage === "kn" ? "ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಯನ್ನು ತಿದ್ದು" : "Edit Major Surgery", cmd: "Edit Major Surgery" },
                  { label: selectedLanguage === "kn" ? "ಆರೈಕೆ ಆದ್ಯತೆಗಳನ್ನು ತಿದ್ದು" : "Edit End-of-Life Preferences", cmd: "Edit End-of-Life Preferences" },
                  { label: selectedLanguage === "kn" ? "ದಾನದ ನಿರ್ಧಾರಗಳನ್ನು ತಿದ್ದು" : "Edit Organ & Body Donation", cmd: "Edit Organ & Body Donation" },
                ].map((act) => (
                  <Button
                    key={act.cmd}
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => handleSend(act.cmd)}
                    disabled={sendMessageMutation.isPending}
                    className="h-8 rounded-lg border-success/30 bg-white text-xs font-medium hover:bg-success/10 text-foreground"
                  >
                    <Edit3 className="mr-1.5 h-3 w-3 text-success" />
                    {act.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </MotionCard>
      )}

      {/* Review & Finalize Card (When Q33 is active) */}
      {isReviewStep && !isPlanCompleted && (
        <MotionCard className="mt-4 border-primary/30 bg-primary/5 p-4 sm:p-5">
          <div className="space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary/20 text-primary">
                  <ListChecks className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">
                    Section 6: Confirmation & Final Review
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Review your complete care plan below. You can make quick adjustments before final confirmation.
                  </p>
                </div>
              </div>

              <Button
                type="button"
                onClick={() => {
                  const pending = nextAcpSection(profile, acpData, dhrData);
                  if (pending !== "review") {
                    window.sessionStorage.setItem("acpReturnToReview", "1");
                    toast.info(
                      selectedLanguage === "kn"
                        ? "ಬಾಕಿ ಇರುವ ವಿವರಗಳನ್ನು ನಮೂದಿಸಲು ACP ಫಾರ್ಮ್ ತೆರೆಯಲಾಗುತ್ತಿದೆ…"
                        : "Opening form to complete remaining required entries..."
                    );
                    navigate({ to: "/patient-dashboard/acp/$section", params: { section: pending } });
                    return;
                  }
                  confirmReviewMutation.mutate();
                }}
                disabled={confirmReviewMutation.isPending}
                className="rounded-xl bg-primary text-xs font-bold text-primary-foreground shadow-sm hover:bg-primary/90"
              >
                {confirmReviewMutation.isPending ? (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-1.5 h-4 w-4" />
                )}
                {selectedLanguage === "kn" ? "ನನ್ನ ಯೋಜನೆಯನ್ನು ದೃಢೀಕರಿಸಿ" : "Confirm & Complete ACP"}
              </Button>
            </div>

            {missingRequiredFields.length > 0 && (
              <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-3">
                <p className="text-sm font-semibold text-foreground">
                  {selectedLanguage === "kn" ? "ಪೂರ್ಣಗೊಳಿಸಲು ಈ ಅಗತ್ಯ ವಿವರಗಳನ್ನು ಸೇರಿಸಿ:" : "Add these required details to complete your ACP:"}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {missingRequiredFields.map((field) => {
                    const section = sectionForMissingField(field);
                    return <Button key={field} size="sm" variant="outline" onClick={() => {
                      window.sessionStorage.setItem("acpReturnToReview", "1");
                      navigate({ to: "/patient-dashboard/acp/$section", params: { section } });
                    }}>{field} <ChevronRight className="ml-1 h-3.5 w-3.5" /></Button>;
                  })}
                </div>
              </div>
            )}

            {/* Quick Edit Buttons */}
            <div className="border-t border-primary/20 pt-3">
              <p className="mb-2 text-xs font-semibold text-muted-foreground">
                {selectedLanguage === "kn"
                  ? "ಅಂತಿಮಗೊಳಿಸುವ ಮೊದಲು ಬದಲಾವಣೆ ಮಾಡಬೇಕೇ? ತಿದ್ದುಪಡಿ ಮಾಡಲು ಒಂದು ವಿಭಾಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ:"
                  : "Need to make a change before finalizing? Select a section to modify:"}
              </p>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: selectedLanguage === "kn" ? "ವೈಯಕ್ತಿಕ ವಿವರಗಳನ್ನು ತಿದ್ದು" : "Edit Personal Details", cmd: "Edit Personal Details" },
                  { label: selectedLanguage === "kn" ? "ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯನ್ನು ತಿದ್ದು" : "Edit Healthcare Representative", cmd: "Edit Healthcare Representative" },
                  { label: selectedLanguage === "kn" ? "ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಗಳನ್ನು ತಿದ್ದು" : "Edit Medical Treatments", cmd: "Edit Medical Treatments" },
                  { label: selectedLanguage === "kn" ? "ಕೀಮೋಥೆರಪಿಯನ್ನು ತಿದ್ದು" : "Edit Chemotherapy", cmd: "Edit Chemotherapy" },
                  { label: selectedLanguage === "kn" ? "ರೇಡಿಯೋಥೆರಪಿಯನ್ನು ತಿದ್ದು" : "Edit Radiotherapy", cmd: "Edit Radiotherapy" },
                  { label: selectedLanguage === "kn" ? "ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಯನ್ನು ತಿದ್ದು" : "Edit Major Surgery", cmd: "Edit Major Surgery" },
                  { label: selectedLanguage === "kn" ? "ಆರೈಕೆ ಆದ್ಯತೆಗಳನ್ನು ತಿದ್ದು" : "Edit End-of-Life Preferences", cmd: "Edit End-of-Life Preferences" },
                  { label: selectedLanguage === "kn" ? "ದಾನದ ನಿರ್ಧಾರಗಳನ್ನು ತಿದ್ದು" : "Edit Organ & Body Donation", cmd: "Edit Organ & Body Donation" },
                ].map((act) => (
                  <Button
                    key={act.cmd}
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => handleSend(act.cmd)}
                    disabled={sendMessageMutation.isPending}
                    className="h-8 rounded-lg border-primary/30 bg-white text-xs font-medium hover:bg-primary/10"
                  >
                    <Edit3 className="mr-1.5 h-3 w-3 text-primary" />
                    {act.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </MotionCard>
      )}

      {/* Session Lost Notice */}
      {sessionLostError && (
        <div className="mt-4 flex items-start justify-between gap-3 rounded-2xl border border-warning/30 bg-warning/10 p-4 text-warning">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="text-sm font-bold text-foreground">Session Inactivity or Server Restart</p>
              <p className="text-xs text-muted-foreground">
                Your questionnaire session was reset or timed out. Please click "Restart Session" to resume.
              </p>
            </div>
          </div>
          <Button size="sm" onClick={handleStart} className="rounded-xl">
            Restart
          </Button>
        </div>
      )}

      {/* Main Chat Container */}
      <MotionCard className="mt-4 max-w-4xl p-0 shadow-sm">
        {/* Chat Header Bar */}
        <div className="flex items-center justify-between border-b border-border p-4 sm:p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand-gradient text-white shadow-xs">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="font-bold text-foreground">ACP Conversational Assistant</div>
              <p className="text-xs text-muted-foreground">
                {activeSession
                  ? `Active Session · Language: ${selectedLanguage === "kn" ? "Kannada" : "English"}`
                  : "Click 'Start Questionnaire' above to begin your advance care planning."}
              </p>
            </div>
          </div>

          {isPlanCompleted && (
            <Badge className="border-success/30 bg-success/10 text-success">Plan Completed</Badge>
          )}
        </div>

        {/* Message Stream */}
        <div
          ref={chatScrollContainerRef}
          className="h-[520px] max-h-[70vh] overflow-y-auto p-4 sm:p-6 space-y-4"
        >
          {/* Initial Welcome Message */}
          {localMessages.length === 0 && !activeSession && (
            <div className="flex items-start gap-3">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-4 w-4" />
              </div>
              <div className="max-w-[85%] rounded-[20px] rounded-tl-sm border border-border bg-surface p-4 text-sm leading-relaxed text-foreground shadow-2xs">
                <p className="font-semibold">
                  Welcome to the Patient-Centered Advance Care Planning Assistant.
                </p>
                <p className="mt-1 text-muted-foreground">
                  This interactive assistant will guide you through all 6 ACP sections: your personal details,
                  medical treatment preferences (CPR, ventilators, dialysis), end-of-life care, healthcare representatives,
                  organ & body donation, and final confirmation.
                </p>
                <div className="mt-4">
                  <Button onClick={handleStart} disabled={startSessionMutation.isPending} className="rounded-xl">
                    {startSessionMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="mr-2 h-4 w-4" />
                    )}
                    Start Questionnaire ({selectedLanguage === "kn" ? "ಕನ್ನಡ" : "English"})
                  </Button>
                </div>
              </div>
            </div>
          )}

          {isLoadingHistory && localMessages.length === 0 && (
            <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading conversation…
            </div>
          )}

          {/* Rendered Messages in Chronological Order */}
          {localMessages.map((msg) => {
            const isUser = msg.from === "user";
            const isQuestion = Boolean(msg.isQuestion);
            const isExplanation = msg.status === "explanation";
            const isInvalid = msg.status === "invalid";
            const hasCannotCompleteText = /cannot complete/i.test(msg.text) || /missing:/i.test(msg.text);
            const isCompleted = msg.status === "completed" && !hasCannotCompleteText;
            const isMissingNotice = !isUser && !isQuestion && hasCannotCompleteText;

            // Determine if this question is the active question awaiting an answer
            const isLatestActiveQuestion =
              isQuestion &&
              !isPlanCompleted &&
              msg.id === activeQuestionMessageId;

            return (
              <div
                key={msg.id}
                className={cn("flex items-start gap-2.5", isUser ? "justify-end" : "justify-start")}
              >
                {!isUser && (
                  <div
                    className={cn(
                      "grid h-7 w-7 shrink-0 place-items-center rounded-full text-white",
                      isQuestion
                        ? "bg-primary text-primary-foreground shadow-2xs"
                        : "bg-primary/10 text-primary"
                    )}
                  >
                    {isQuestion ? <HelpCircle className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                  </div>
                )}

                <div
                  className={cn(
                    "max-w-[82%] rounded-[20px] p-4 text-sm leading-relaxed shadow-2xs",
                    isUser
                      ? "rounded-tr-sm bg-primary text-primary-foreground"
                      : isQuestion
                        ? "rounded-tl-sm border-2 border-primary/20 bg-primary/5 text-foreground shadow-xs"
                        : isExplanation
                          ? "rounded-tl-sm border border-brand-teal/30 bg-brand-teal/5 text-foreground"
                          : isMissingNotice
                            ? "rounded-tl-sm border border-warning/40 bg-warning/5 text-foreground"
                            : isInvalid
                              ? "rounded-tl-sm border border-warning/30 bg-warning/5 text-foreground"
                              : isCompleted
                                ? "rounded-tl-sm border border-success/30 bg-success/5 text-foreground"
                                : "rounded-tl-sm border border-border bg-surface text-foreground"
                  )}
                >
                  {/* Question Header Badge */}
                  {isQuestion && (
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-bold text-primary">
                      <Badge variant="outline" className="border-primary/30 bg-white text-[10px] uppercase font-bold text-primary">
                        {selectedLanguage === "kn" ? "ಪ್ರಶ್ನೆ" : "Question"}
                      </Badge>
                    </div>
                  )}

                  {/* Status header tags */}
                  {isExplanation && (
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-brand-teal">
                      <BookOpen className="h-3.5 w-3.5" /> Educational Information (Unsure)
                    </div>
                  )}
                  {isMissingNotice ? (
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-warning">
                      <AlertCircle className="h-3.5 w-3.5" /> {selectedLanguage === "kn" ? "ಅಪೂರ್ಣ ವಿವರಗಳು - ಕ್ರಮ ಅಗತ್ಯವಿದೆ" : "Action Required — Incomplete Details"}
                    </div>
                  ) : isInvalid ? (
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-warning">
                      <AlertCircle className="h-3.5 w-3.5" /> Input Not Recognized
                    </div>
                  ) : null}
                  {isCompleted && (
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-success">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Plan Finalized
                    </div>
                  )}

                  <div className={cn("whitespace-pre-wrap", isQuestion && "font-semibold text-foreground")}>
                    {msg.text}
                  </div>
                  {isMissingNotice && (
                    <div className="mt-3 border-t border-warning/20 pt-2.5">
                      <Button
                        type="button"
                        size="sm"
                        className="rounded-lg bg-primary text-xs font-semibold text-primary-foreground shadow-xs hover:bg-primary/90"
                        onClick={() => {
                          const missingMatch = msg.text.match(/missing:\s*(.+?)(?:\.|$)/i)?.[1];
                          const fields = missingMatch ? missingMatch.split(/,\s*/).filter(Boolean) : [];
                          const missingSections = fields.map((f: string) => sectionForMissingField(f));
                          const firstIncomplete = ACP_SECTIONS.find((s) => missingSections.includes(s.key))?.key;
                          const target =
                            firstIncomplete ||
                            (nextAcpSection(profile, acpData, dhrData) !== "review"
                              ? nextAcpSection(profile, acpData, dhrData)
                              : "personal");
                          window.sessionStorage.setItem("acpReturnToReview", "1");
                          navigate({
                            to: "/patient-dashboard/acp/$section",
                            params: { section: target },
                          });
                        }}
                      >
                        {selectedLanguage === "kn"
                          ? "ಬಾಕಿ ಇರುವ ವಿವರಗಳನ್ನು ಭರ್ತಿ ಮಾಡಲು ಫಾರ್ಮ್ ತೆರೆಯಿರಿ"
                          : "Open Form to Complete Remaining Details"}
                        <ChevronRight className="ml-1 h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                  {isQuestion && isLatestActiveQuestion && validationError && Number(validationError.questionNumber) === Number(msg.questionNumber) && (
                    <p role="alert" className="mt-2 flex items-center gap-1.5 text-xs font-medium text-destructive"><AlertCircle className="h-3.5 w-3.5" />{validationError.message}</p>
                  )}

                  {/* Predefined Choice Pills inside Question Card */}
                  {isQuestion && msg.options && msg.options.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2 pt-2 border-t border-primary/10">
                      {msg.options.map((opt) => (
                        <Button
                          key={opt}
                          type="button"
                          size="sm"
                          variant={isLatestActiveQuestion ? "secondary" : "outline"}
                          onClick={() => isLatestActiveQuestion && handleSendOption(opt)}
                          disabled={sendMessageMutation.isPending || !isLatestActiveQuestion}
                          className={cn(
                            "rounded-lg text-xs font-medium transition",
                            isLatestActiveQuestion
                              ? "border border-primary/30 bg-white hover:border-primary hover:bg-primary/10 text-foreground cursor-pointer shadow-2xs"
                              : "border-border/50 bg-surface text-muted-foreground opacity-75 cursor-default"
                          )}
                        >
                          {opt}
                        </Button>
                      ))}
                    </div>
                  )}

                  {isQuestion &&
                    isLatestActiveQuestion &&
                    [20, 22, 31, 32].includes(msg.questionNumber || -1) &&
                    !(msg.options || []).some((option: string) => ["skip", "ಬಿಟ್ಟುಬಿಡಿ"].includes(option.toLowerCase())) && (
                      <div className="mt-3 border-t border-primary/10 pt-2">
                        <Button type="button" size="sm" variant="outline" onClick={() => handleSend("Skip")} disabled={sendMessageMutation.isPending}>
                          {selectedLanguage === "kn" ? "ಬಿಟ್ಟುಬಿಡಿ" : "Skip"}
                        </Button>
                      </div>
                    )}

                  {/* Sources citations if available */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 border-t border-border/50 pt-2 text-xs text-muted-foreground">
                      <span className="font-semibold">References: </span>
                      {msg.sources.map((s, idx) => (
                        <span key={idx} className="mr-2 inline-block italic">
                          [{s.source}]
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-secondary text-secondary-foreground">
                    <User className="h-3.5 w-3.5" />
                  </div>
                )}
              </div>
            );
          })}

          {sendMessageMutation.isPending && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span>Recording clinical preferences…</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>


        {/* Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2 border-t border-border p-4"
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              !activeSession
                ? "Click 'Start Questionnaire' above to begin…"
                : isPlanCompleted
                  ? "Plan completed! You can ask general advance care planning questions here…"
                  : isReviewStep
                    ? "Type 'Confirm & Complete ACP' or choose a section above to edit…"
                    : Number(currentQuestionData?.question_number) === 2
                      ? (selectedLanguage === "kn" ? "ಜನ್ಮ ದಿನಾಂಕವನ್ನು DD/MM/YYYY ನಮೂದಿಸಿ…" : "Enter date of birth (DD/MM/YYYY)…")
                      : (selectedLanguage === "kn" ? "ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಇಲ್ಲಿ ನಮೂದಿಸಿ ಅಥವಾ ಮೇಲಿನ ಆಯ್ಕೆಮಾಡಿ…" : "Type your answer or select an option above…")
            }
            disabled={!activeSession || sendMessageMutation.isPending}
            className="h-11 flex-1 rounded-xl border border-border bg-surface px-4 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
          />
          <Button
            type="submit"
            disabled={!draft.trim() || !activeSession || sendMessageMutation.isPending}
            className="h-11 rounded-xl px-5"
          >
            {sendMessageMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Send className="mr-2 h-4 w-4" />
            )}
            Send
          </Button>
        </form>
      </MotionCard>

      {/* Restart Questionnaire Confirmation Dialog */}
      <AlertDialog open={showRestartDialog} onOpenChange={setShowRestartDialog}>
        <AlertDialogContent className="rounded-2xl max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-lg font-bold text-foreground">
              {selectedLanguage === "kn"
                ? "ಪ್ರಶ್ನಾವಳಿಯನ್ನು ಮರುಪ್ರಾರಂಭಿಸಬೇಕೇ?"
                : "Restart Questionnaire Session?"}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm text-muted-foreground leading-relaxed">
              {selectedLanguage === "kn"
                ? "ನೀವು ಪ್ರಶ್ನಾವಳಿಯನ್ನು ಮೊದಲಿನಿಂದ ಮರುಪ್ರಾರಂಭಿಸಲು ಖಚಿತವಾಗಿ ಬಯಸುತ್ತೀರಾ? ಈ ಕ್ರಿಯೆಯು ನಿಮ್ಮ ಎಲ್ಲಾ ಉತ್ತರಗಳನ್ನು ತೆರವುಗೊಳಿಸುತ್ತದೆ ಮತ್ತು ಪ್ರಗತಿ 0% ಗೆ ಮರಳಿಸುತ್ತದೆ. ಸಲ್ಲಿಸಲ್ಪಟ್ಟ ಅಥವಾ ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟ ಯೋಜನೆಗಳು ಸಂರಕ್ಷಿತವಾಗಿರುತ್ತವೆ."
                : "Are you sure you want to restart your Advance Care Planning questionnaire from the beginning? This will clear all your draft answers and reset your progress to 0%. Submitted or reviewed plans are preserved."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-4 gap-2">
            <AlertDialogCancel className="rounded-xl">
              {selectedLanguage === "kn" ? "ರದ್ದುಮಾಡಿ" : "Cancel"}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setShowRestartDialog(false);
                restartSessionMutation.mutate(selectedLanguage);
              }}
              className="rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {restartSessionMutation.isPending
                ? (selectedLanguage === "kn" ? "ಮರುಪ್ರಾರಂಭಿಸಲಾಗುತ್ತಿದೆ…" : "Restarting…")
                : (selectedLanguage === "kn" ? "ಹೌದು, ಮರುಪ್ರಾರಂಭಿಸಿ" : "Yes, Restart Session")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PatientShell>
  );
}
