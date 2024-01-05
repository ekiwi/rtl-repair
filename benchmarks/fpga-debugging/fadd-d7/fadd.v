module fadd #(parameter N = 32, parameter E = 8, parameter S = 1) (
    // Inputs
    input logic         clk,
    input logic         rst,
    input logic         en,
    input logic [N-1:0] op1,
    input logic [N-1:0] op2,

    // Outputs
    output logic         res_val,
    output logic [N-1:0] res
);

    logic             op1_sign, op1_sign_next, op2_sign, op2_sign_next;
    logic [E-1:0]     op1_exp, op1_exp_next, op2_exp, op2_exp_next;
    logic [N-E-S-1:0] op1_mant, op1_mant_next, op2_mant, op2_mant_next;
    logic             tmp_sign, tmp_sign_next;
    logic [E-1:0]     tmp_exp, tmp_exp_next;
    logic [N-E:0]     tmp_mant, tmp_mant_next;
    logic [E-1:0]     exp_diff, exp_diff_next;
    logic             res_sign_next;
    logic [E-1:0]     res_exp_next;
    logic [N-E-S-1:0] res_mant_next;
    logic             en_saved, en_saved_next, en_saved_2, en_saved_2_next, res_val_next;
    logic             zero, zero_next;

    always_comb begin
        zero_next       = '0;
        en_saved_next   = en;
        en_saved_2_next = en_saved;
        res_val_next    = en_saved_2;

        op1_sign_next = op1[N-1];
        op1_exp_next  = op1[N-S-1:N-E-1];
        op1_mant_next = op1[N-E-S-1:0];

        op2_sign_next = op2[N-1];
        op2_exp_next  = op2[N-S-1:N-E-1];
        op2_mant_next = op2[N-E-S-1:0];

        exp_diff_next = '0;

        tmp_sign_next = '0;
        tmp_exp_next  = '0;
        tmp_mant_next = '0;

        res_sign_next = '0;
        res_exp_next  = '0;
        res_mant_next = '0;

        // Cycle 0 - sort operands (find larger) and calculate exponent difference
        if(en) begin
            // Check if either operand is zero
            if(op1[N-S-1:N-E-1] == 0 && op1[N-E-S-1:0] == 0) begin
                zero_next = 1'b1;
            end else if(op2[N-S-1:N-E-1] == 0 && op2[N-E-S-1:0] == 0) begin
                zero_next = 1'b1;
            end

            if((op2[N-S-1:N-E-1] > op1[N-S-1:N-E-1]) || ((op2[N-S-1:N-E-1] == op1[N-S-1:N-E-1]) && (op2[N-E-S-1:0] > op1[N-E-S-1:0]))) begin
                op1_sign_next = op2[N-1];
                op1_exp_next  = op2[N-S-1:N-E-1];
                op1_mant_next = op2[N-E-S-1:0];

                op2_sign_next = op1[N-1];
                op2_exp_next  = op1[N-S-1:N-E-1];
                op2_mant_next = op1[N-E-S-1:0];
            end
        end
        exp_diff_next = op1_exp_next - op2_exp_next;

        // Cycle 1 - normalize operands and perform the addition
        if(en_saved) begin
            tmp_sign_next = op1_sign;
            tmp_exp_next = op1_exp;
            if(zero) begin
                tmp_mant_next = {1'b1, op1_mant};
            end else if(op1_sign == op2_sign) begin
                tmp_mant_next = {1'b1, op1_mant} + ({1'b1, op2_mant} >> exp_diff);
            end else begin
                tmp_mant_next = {1'b1, op1_mant} - ({1'b1, op2_mant} >> exp_diff);
            end
        end

        // Cycle 2 - normalize the result
        if(en_saved_2) begin
            if(tmp_mant != 0) begin
                res_sign_next = tmp_sign;
            end

            if(tmp_mant[N-E]) begin
                res_exp_next = tmp_exp + 1;
                res_mant_next = tmp_mant[N-E:1];
            end else begin
                for(int i = 0; i < N-E-1; i = i + 1) begin
                    if(tmp_mant[N-E-1-i]) begin
                        // Check for underflow
                        if(i > tmp_exp) begin
                            res_exp_next = 1;
                        end else begin
                            res_exp_next = tmp_exp - i;
                            res_mant_next = tmp_mant[N-E-S-1:0] << i;
                        end

                        break;
                    end
                end
            end
        end
    end

    always_ff @(posedge clk) begin
        if(rst) begin
            zero       <= '0;
            en_saved   <= '0;
            en_saved_2 <= '0;

            op1_sign <= '0;
            op1_exp  <= '0;
            op1_mant <= '0;
            op2_sign <= '0;
            op2_exp  <= '0;
            op2_mant <= '0;

            exp_diff <= '0;

            tmp_sign <= '0;
            tmp_exp  <= '0;
            tmp_mant <= '0;

            res_val <= '0;
            res     <= '0;
        end else begin
            zero       <= zero_next;
            en_saved   <= en_saved_next;
            en_saved_2 <= en_saved_2_next;

            op1_sign <= op1_sign_next;
            op1_exp  <= op1_exp_next;
            op1_mant <= op1_mant_next;
            op2_sign <= op2_sign_next;
            op2_exp  <= op2_exp_next;
            op2_mant <= op2_mant_next;

            exp_diff <= exp_diff_next;

            tmp_sign <= tmp_sign_next;
            tmp_exp  <= tmp_exp_next;
            tmp_mant <= tmp_mant_next;

            res_val <= res_val_next;
            res     <= {res_sign_next, res_exp_next, res_mant_next};
        end
    end

endmodule
