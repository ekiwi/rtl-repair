module BM_lamda
(
  input clk,
  input reset,
  input [7:0] Sm1,
  input [7:0] Sm2,
  input [7:0] Sm3,
  input [7:0] Sm4,
  input [7:0] Sm5,
  input [7:0] Sm6,
  input [7:0] Sm7,
  input [7:0] Sm8,
  input [7:0] Sm9,
  input [7:0] Sm10,
  input [7:0] Sm11,
  input [7:0] Sm12,
  input [7:0] Sm13,
  input [7:0] Sm14,
  input [7:0] Sm15,
  input [7:0] Sm16,
  input Sm_ready,
  input erasure_ready,
  input [3:0] erasure_cnt,
  input [7:0] pow1,
  input [7:0] pow2,
  input [7:0] dec1,
  output reg [7:0] add_pow1,
  output reg [7:0] add_pow2,
  output [7:0] add_dec1,
  output reg L_ready,
  output [7:0] L1,
  output [7:0] L2,
  output [7:0] L3,
  output [7:0] L4,
  output [7:0] L5,
  output [7:0] L6,
  output [7:0] L7,
  output [7:0] L8
);

  reg [7:0] L [1:9];
  reg [7:0] Lt [1:9];
  reg [7:0] T [1:10];
  reg [7:0] D;
  reg [4:0] K;
  reg [3:0] N;
  reg [3:0] e_cnt;
  reg [7:0] S [1:16];
  reg [8:0] add_1;
  reg IS_255_1;
  reg div1;
  reg [3:0] cnt;
  parameter Step1 = 8'b00000001;
  parameter Step2 = 8'b00000010;
  parameter Step3 = 8'b00000100;
  parameter Step4 = 8'b00001000;
  parameter Step5 = 8'b00010000;
  parameter Step6 = 8'b00100000;
  parameter Step7 = 8'b01000000;
  parameter Step8 = 8'b10000000;
  reg [8:0] const_timing;
  reg [7:0] Step;assign Step = Step1;
  assign L1 = L[2];
  assign L2 = L[3];
  assign L3 = L[4];
  assign L4 = L[5];
  assign L5 = L[6];
  assign L6 = L[7];
  assign L7 = L[8];
  assign L8 = L[9];
  assign add_dec1 = (IS_255_1)? 8'h00 : 
                    (&add_1[7:0] && !add_1[8])? 8'h01 : 
                    (div1)? add_1[7:0] - add_1[8] + 1 : add_1[7:0] + add_1[8] + 1;

  always @(posedge reset or posedge clk) begin
    if(reset) begin
      add_1 <= 0;
      IS_255_1 <= 0;
      div1 <= 0;
      add_pow1 <= 0;
      add_pow2 <= 0;
      e_cnt <= 0;
      S[1] <= 0;
      S[2] <= 0;
      S[3] <= 0;
      S[4] <= 0;
      S[5] <= 0;
      S[6] <= 0;
      S[7] <= 0;
      S[8] <= 0;
      S[9] <= 0;
      S[10] <= 0;
      S[11] <= 0;
      S[12] <= 0;
      S[13] <= 0;
      S[14] <= 0;
      S[15] <= 0;
      S[16] <= 0;
      L[1] <= 0;
      L[2] <= 0;
      L[3] <= 0;
      L[4] <= 0;
      L[5] <= 0;
      L[6] <= 0;
      L[7] <= 0;
      L[8] <= 0;
      L[9] <= 0;
      Lt[1] <= 0;
      Lt[2] <= 0;
      Lt[3] <= 0;
      Lt[4] <= 0;
      Lt[5] <= 0;
      Lt[6] <= 0;
      Lt[7] <= 0;
      Lt[8] <= 0;
      Lt[9] <= 0;
      T[1] <= 0;
      T[2] <= 0;
      T[3] <= 0;
      T[4] <= 0;
      T[5] <= 0;
      T[6] <= 0;
      T[7] <= 0;
      T[8] <= 0;
      T[9] <= 0;
      T[10] <= 0;
      D <= 0;
      K <= 0;
      N <= 0;
      cnt <= 0;
      Step <= Step1;
      L_ready <= 0;
      const_timing <= 0;
    end else begin
      case(Step)
        default: begin
          L[1] <= 1;
          L[2] <= 0;
          L[3] <= 0;
          L[4] <= 0;
          L[5] <= 0;
          L[6] <= 0;
          L[7] <= 0;
          L[8] <= 0;
          L[9] <= 0;
          Lt[1] <= 1;
          Lt[2] <= 0;
          Lt[3] <= 0;
          Lt[4] <= 0;
          Lt[5] <= 0;
          Lt[6] <= 0;
          Lt[7] <= 0;
          Lt[8] <= 0;
          Lt[9] <= 0;
          T[1] <= 0;
          T[2] <= 1;
          T[3] <= 0;
          T[4] <= 0;
          T[5] <= 0;
          T[6] <= 0;
          T[7] <= 0;
          T[8] <= 0;
          T[9] <= 0;
          T[10] <= 0;
          D <= 0;
          K <= 0;
          N <= 0;
          cnt <= 0;
          L_ready <= 0;
          if(erasure_ready) begin
            e_cnt <= erasure_cnt;
          end 
          if(Sm_ready) begin
            Step <= Step2;
            S[1] <= Sm1;
            S[2] <= Sm2;
            S[3] <= Sm3;
            S[4] <= Sm4;
            S[5] <= Sm5;
            S[6] <= Sm6;
            S[7] <= Sm7;
            S[8] <= Sm8;
            S[9] <= Sm9;
            S[10] <= Sm10;
            S[11] <= Sm11;
            S[12] <= Sm12;
            S[13] <= Sm13;
            S[14] <= Sm14;
            S[15] <= Sm15;
            S[16] <= Sm16;
          end 
        end
        Step2: begin
          K <= K + 1;
          Step <= Step3;
        end
        Step3: begin
          if(N == 0) begin
            D <= S[K + e_cnt];
            if(S[K + e_cnt] == 0) Step <= Step6; 
            else Step <= Step4;
          end else begin
            if(cnt == N + 4) begin
              cnt <= 0;
              if((D ^ dec1) == 0) Step <= Step6; 
              else Step <= Step4;
            end else cnt <= cnt + 1;
            if(cnt == 0) begin
              D <= S[K + e_cnt];
            end else if(cnt < 5) begin
              add_pow1 <= L[cnt + 1];
              add_pow2 <= S[K + e_cnt - cnt];
              div1 <= 0;
              add_1 <= pow1 + pow2;
              IS_255_1 <= (&pow1 || &pow2)? 1 : 0;
            end else begin
              add_pow1 <= L[cnt + 1];
              add_pow2 <= S[K + e_cnt - cnt];
              div1 <= 0;
              add_1 <= pow1 + pow2;
              IS_255_1 <= (&pow1 || &pow2)? 1 : 0;
              D <= D ^ dec1;
            end
          end
        end
        Step4: begin
          if(cnt == 11 - e_cnt[3:1]) begin
            cnt <= 0;
            Step <= Step5;
          end else cnt <= cnt + 1;
          add_pow1 <= T[cnt + 2];
          add_pow2 <= D;
          div1 <= 0;
          add_1 <= pow1 + pow2;
          IS_255_1 <= (&pow1 || &pow2)? 1 : 0;
          if(cnt > 3) begin
            Lt[cnt - 2] <= L[cnt - 2] ^ dec1;
          end 
        end
        Step5: begin
          if({ N, 1'b0 } >= K) begin
            Step <= Step6;
            L[1] <= Lt[1];
            L[2] <= Lt[2];
            L[3] <= Lt[3];
            L[4] <= Lt[4];
            L[5] <= Lt[5];
            L[6] <= Lt[6];
            L[7] <= Lt[7];
            L[8] <= Lt[8];
            L[9] <= Lt[9];
          end else begin
            if(cnt == 12 - e_cnt[3:1]) begin
              cnt <= 0;
              Step <= Step6;
              N <= K - N;
              L[1] <= Lt[1];
              L[2] <= Lt[2];
              L[3] <= Lt[3];
              L[4] <= Lt[4];
              L[5] <= Lt[5];
              L[6] <= Lt[6];
              L[7] <= Lt[7];
              L[8] <= Lt[8];
              L[9] <= Lt[9];
            end else cnt <= cnt + 1;
            add_pow1 <= L[cnt + 1];
            add_pow2 <= D;
            div1 <= 1;
            add_1 <= pow1 - pow2;
            IS_255_1 <= (&pow1 || &pow2)? 1 : 0;
            if(cnt > 3) begin
              T[cnt - 3] <= dec1;
            end 
          end
        end
        Step6: begin
          Step <= Step7;
          T[1] <= 0;
          T[2] <= T[1];
          T[3] <= T[2];
          T[4] <= T[3];
          T[5] <= T[4];
          T[6] <= T[5];
          T[7] <= T[6];
          T[8] <= T[7];
          T[9] <= T[8];
          T[10] <= T[9];
        end
        Step7: begin
          if(K < 16 - e_cnt) Step <= Step2; 
          else begin
            Step <= Step8;
          end
        end
        Step8: begin
          if(const_timing == 0) begin
            L_ready <= 1;
            Step <= Step1;
          end 
        end
      endcase
      if(Step == Step1) begin
        const_timing <= 500;
      end else begin
        const_timing <= const_timing - 1;
      end
    end
  end


endmodule
