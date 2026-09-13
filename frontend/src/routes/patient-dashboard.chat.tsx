import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Send, Sparkles } from "lucide-react";
import { PatientShell } from "@/components/patient-shell";
import { Button } from "@/components/ui/button";
import { MotionCard } from "@/components/motion-card";
import { chatService, patientService } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/patient-dashboard/chat")({ component: ChatPage });

function ChatPage() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const { data: profile } = useQuery({ queryKey: ["patientProfile"], queryFn: patientService.getProfile });
  const patientId = profile?.patient_id;
  const { data: history = [], isLoading } = useQuery({ queryKey: ["chatHistory", patientId], queryFn: () => chatService.getHistory(patientId), enabled: !!patientId });
  const send = useMutation({
    mutationFn: (message: string) => chatService.processChat({ patient_id: patientId, message }),
    onSuccess: () => { setDraft(""); queryClient.invalidateQueries({ queryKey: ["chatHistory", patientId] }); },
    onError: (error: Error) => toast.error(error.message),
  });
  const messages = history.flatMap((item: any) => [
    { id: `${item.id}-user`, from: "user", text: item.user_message },
    { id: `${item.id}-bot`, from: "bot", text: item.bot_response },
  ]);
  const submit = (event: React.FormEvent) => { event.preventDefault(); if (draft.trim() && patientId) send.mutate(draft.trim()); };

  return <PatientShell>
    <header><h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">ACP Chatbot</h1><p className="mt-1 text-sm text-muted-foreground">Talk through your care preferences at your own pace.</p></header>
    <MotionCard className="mt-6 max-w-4xl p-0">
      <div className="flex items-center gap-3 border-b border-border p-5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-brand-gradient text-white"><Sparkles className="h-5 w-5" /></div><div><div className="font-bold">ACP Assistant</div><p className="text-xs text-muted-foreground">Your conversation is stored securely in your ACP record.</p></div></div>
      <div className="min-h-[420px] space-y-4 px-5 py-6">
        <div className="flex"><div className="max-w-[78%] rounded-[20px] rounded-bl-md bg-surface px-4 py-3 text-sm shadow-sm">Welcome to ACP Care. I�m here to help you express your wishes for future care. What would you like to talk about?</div></div>
        {isLoading ? <p className="text-sm text-muted-foreground">Loading your conversation�</p> : messages.map((message: any) => <div key={message.id} className={cn("flex", message.from === "user" ? "justify-end" : "justify-start")}><div className={cn("max-w-[78%] rounded-[20px] px-4 py-3 text-sm leading-relaxed shadow-sm", message.from === "user" ? "rounded-br-md bg-primary text-primary-foreground" : "rounded-bl-md bg-surface text-foreground")}>{message.text}</div></div>)}
      </div>
      <form onSubmit={submit} className="flex gap-2 border-t border-border p-4"><input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Type your response�" className="h-11 flex-1 rounded-xl border border-border bg-surface px-4 text-sm outline-none focus:ring-2 focus:ring-primary/30" /><Button type="submit" disabled={!patientId || send.isPending} className="h-11 rounded-xl"><Send className="mr-2 h-4 w-4" />{send.isPending ? "Sending" : "Send"}</Button></form>
    </MotionCard>
  </PatientShell>;
}