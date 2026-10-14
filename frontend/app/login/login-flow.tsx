"use client";
import { AuthProvider, Descope } from "@descope/nextjs-sdk";
import { useState } from "react";

export function LoginFlow({projectId}:{projectId:string}){
  const [message,setMessage]=useState("");
  return <AuthProvider projectId={projectId}>
    <Descope flowId="sign-up-or-in" theme="light"
      onSuccess={() => setMessage("Login confirmado pelo Descope. A sessão de acesso às obras ainda requer integração com o backend.")}
      onError={() => setMessage("Falha na autenticação. Verifique o fluxo e tente novamente.")}/>
    <p role="status">{message}</p>
  </AuthProvider>;
}
