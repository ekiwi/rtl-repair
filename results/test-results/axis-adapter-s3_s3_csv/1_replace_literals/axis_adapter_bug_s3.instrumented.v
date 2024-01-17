

module axis_adapter #
(
  parameter INPUT_DATA_WIDTH = 64,
  parameter INPUT_KEEP_WIDTH = INPUT_DATA_WIDTH / 8,
  parameter OUTPUT_DATA_WIDTH = 8,
  parameter OUTPUT_KEEP_WIDTH = OUTPUT_DATA_WIDTH / 8
)
(
  input wire clk,
  input wire rst,
  input wire [INPUT_DATA_WIDTH-1:0] input_axis_tdata,
  input wire [INPUT_KEEP_WIDTH-1:0] input_axis_tkeep,
  input wire input_axis_tvalid,
  output wire input_axis_tready,
  input wire input_axis_tlast,
  input wire input_axis_tuser,
  output wire [OUTPUT_DATA_WIDTH-1:0] output_axis_tdata,
  output wire [OUTPUT_KEEP_WIDTH-1:0] output_axis_tkeep,
  output wire output_axis_tvalid,
  input wire output_axis_tready,
  output wire output_axis_tlast,
  output wire output_axis_tuser
);

  reg __synth_change_literal_0 = $anyconst;
  reg __synth_change_literal_1 = $anyconst;
  reg __synth_change_literal_2 = $anyconst;
  reg __synth_change_literal_3 = $anyconst;
  reg __synth_change_literal_4 = $anyconst;
  reg __synth_change_literal_5 = $anyconst;
  reg __synth_change_literal_6 = $anyconst;
  reg __synth_change_literal_7 = $anyconst;
  reg __synth_change_literal_8 = $anyconst;
  reg __synth_change_literal_9 = $anyconst;
  reg __synth_change_literal_10 = $anyconst;
  reg __synth_change_literal_11 = $anyconst;
  reg __synth_change_literal_12 = $anyconst;
  reg __synth_change_literal_13 = $anyconst;
  reg __synth_change_literal_14 = $anyconst;
  reg __synth_change_literal_15 = $anyconst;
  reg __synth_change_literal_16 = $anyconst;
  reg __synth_change_literal_17 = $anyconst;
  reg __synth_change_literal_18 = $anyconst;
  reg __synth_change_literal_19 = $anyconst;
  reg __synth_change_literal_20 = $anyconst;
  reg __synth_change_literal_21 = $anyconst;
  reg __synth_change_literal_22 = $anyconst;
  reg __synth_change_literal_23 = $anyconst;
  reg __synth_change_literal_24 = $anyconst;
  reg __synth_change_literal_25 = $anyconst;
  reg __synth_change_literal_26 = $anyconst;
  reg __synth_change_literal_27 = $anyconst;
  reg __synth_change_literal_28 = $anyconst;
  reg __synth_change_literal_29 = $anyconst;
  reg __synth_change_literal_30 = $anyconst;
  reg __synth_change_literal_31 = $anyconst;
  reg __synth_change_literal_32 = $anyconst;
  reg __synth_change_literal_33 = $anyconst;
  reg __synth_change_literal_34 = $anyconst;
  reg __synth_change_literal_35 = $anyconst;
  reg __synth_change_literal_36 = $anyconst;
  reg __synth_change_literal_37 = $anyconst;
  reg __synth_change_literal_38 = $anyconst;
  reg __synth_change_literal_39 = $anyconst;
  reg __synth_change_literal_40 = $anyconst;
  reg __synth_change_literal_41 = $anyconst;
  reg __synth_change_literal_42 = $anyconst;
  reg __synth_change_literal_43 = $anyconst;
  reg __synth_change_literal_44 = $anyconst;
  reg __synth_change_literal_45 = $anyconst;
  reg __synth_change_literal_46 = $anyconst;
  reg __synth_change_literal_47 = $anyconst;
  reg __synth_change_literal_48 = $anyconst;
  reg __synth_change_literal_49 = $anyconst;
  reg __synth_change_literal_50 = $anyconst;
  reg __synth_change_literal_51 = $anyconst;
  reg __synth_change_literal_52 = $anyconst;
  reg __synth_change_literal_53 = $anyconst;
  reg __synth_change_literal_54 = $anyconst;
  reg __synth_change_literal_55 = $anyconst;
  reg __synth_change_literal_56 = $anyconst;
  reg __synth_change_literal_57 = $anyconst;
  reg __synth_change_literal_58 = $anyconst;
  reg __synth_change_literal_59 = $anyconst;
  reg __synth_change_literal_60 = $anyconst;
  reg __synth_change_literal_61 = $anyconst;
  reg __synth_change_literal_62 = $anyconst;
  reg __synth_change_literal_63 = $anyconst;
  reg __synth_change_literal_64 = $anyconst;
  reg __synth_change_literal_65 = $anyconst;
  reg __synth_change_literal_66 = $anyconst;
  reg __synth_change_literal_67 = $anyconst;
  reg __synth_change_literal_68 = $anyconst;
  reg __synth_change_literal_69 = $anyconst;
  reg __synth_change_literal_70 = $anyconst;
  reg __synth_change_literal_71 = $anyconst;
  reg __synth_change_literal_72 = $anyconst;
  reg __synth_change_literal_73 = $anyconst;
  reg __synth_change_literal_74 = $anyconst;
  reg __synth_change_literal_75 = $anyconst;
  reg __synth_change_literal_76 = $anyconst;
  reg __synth_change_literal_77 = $anyconst;
  reg __synth_change_literal_78 = $anyconst;
  reg __synth_change_literal_79 = $anyconst;
  reg __synth_change_literal_80 = $anyconst;
  reg __synth_change_literal_81 = $anyconst;
  reg __synth_change_literal_82 = $anyconst;
  reg __synth_change_literal_83 = $anyconst;
  reg __synth_change_literal_84 = $anyconst;
  reg __synth_change_literal_85 = $anyconst;
  reg __synth_change_literal_86 = $anyconst;
  reg __synth_change_literal_87 = $anyconst;
  reg __synth_change_literal_88 = $anyconst;
  reg __synth_change_literal_89 = $anyconst;
  reg __synth_change_literal_90 = $anyconst;
  reg __synth_change_literal_91 = $anyconst;
  reg __synth_change_literal_92 = $anyconst;
  reg __synth_change_literal_93 = $anyconst;
  reg __synth_change_literal_94 = $anyconst;
  reg __synth_change_literal_95 = $anyconst;
  reg __synth_change_literal_96 = $anyconst;
  reg [2:0] __synth_literal_0 = $anyconst;
  reg [7:0] __synth_literal_1 = $anyconst;
  reg [7:0] __synth_literal_2 = $anyconst;
  reg [7:0] __synth_literal_3 = $anyconst;
  reg [7:0] __synth_literal_4 = $anyconst;
  reg [7:0] __synth_literal_5 = $anyconst;
  reg [7:0] __synth_literal_6 = $anyconst;
  reg [2:0] __synth_literal_7 = $anyconst;
  reg [31:0] __synth_literal_8 = $anyconst;
  reg [31:0] __synth_literal_9 = $anyconst;
  reg [2:0] __synth_literal_10 = $anyconst;
  reg __synth_literal_11 = $anyconst;
  reg [31:0] __synth_literal_12 = $anyconst;
  reg [31:0] __synth_literal_13 = $anyconst;
  reg [7:0] __synth_literal_14 = $anyconst;
  reg [2:0] __synth_literal_15 = $anyconst;
  reg [31:0] __synth_literal_16 = $anyconst;
  reg [2:0] __synth_literal_17 = $anyconst;
  reg [2:0] __synth_literal_18 = $anyconst;
  reg [31:0] __synth_literal_19 = $anyconst;
  reg [7:0] __synth_literal_20 = $anyconst;
  reg [31:0] __synth_literal_21 = $anyconst;
  reg [31:0] __synth_literal_22 = $anyconst;
  reg [31:0] __synth_literal_23 = $anyconst;
  reg __synth_literal_24 = $anyconst;
  reg [31:0] __synth_literal_25 = $anyconst;
  reg [31:0] __synth_literal_26 = $anyconst;
  reg __synth_literal_27 = $anyconst;
  reg [31:0] __synth_literal_28 = $anyconst;
  reg [7:0] __synth_literal_29 = $anyconst;
  reg [2:0] __synth_literal_30 = $anyconst;
  reg [2:0] __synth_literal_31 = $anyconst;
  reg [2:0] __synth_literal_32 = $anyconst;
  reg [31:0] __synth_literal_33 = $anyconst;
  reg [31:0] __synth_literal_34 = $anyconst;
  reg [31:0] __synth_literal_35 = $anyconst;
  reg [31:0] __synth_literal_36 = $anyconst;
  reg [2:0] __synth_literal_37 = $anyconst;
  reg [31:0] __synth_literal_38 = $anyconst;
  reg [2:0] __synth_literal_39 = $anyconst;
  reg [2:0] __synth_literal_40 = $anyconst;
  reg [2:0] __synth_literal_41 = $anyconst;
  reg __synth_literal_42 = $anyconst;
  reg [7:0] __synth_literal_43 = $anyconst;
  reg [31:0] __synth_literal_44 = $anyconst;
  reg [31:0] __synth_literal_45 = $anyconst;
  reg [7:0] __synth_literal_46 = $anyconst;
  reg [2:0] __synth_literal_47 = $anyconst;
  reg [31:0] __synth_literal_48 = $anyconst;
  reg [2:0] __synth_literal_49 = $anyconst;
  reg [31:0] __synth_literal_50 = $anyconst;
  reg [2:0] __synth_literal_51 = $anyconst;
  reg [2:0] __synth_literal_52 = $anyconst;
  reg [7:0] __synth_literal_53 = $anyconst;
  reg [31:0] __synth_literal_54 = $anyconst;
  reg [31:0] __synth_literal_55 = $anyconst;
  reg [31:0] __synth_literal_56 = $anyconst;
  reg [31:0] __synth_literal_57 = $anyconst;
  reg [31:0] __synth_literal_58 = $anyconst;
  reg [31:0] __synth_literal_59 = $anyconst;
  reg __synth_literal_60 = $anyconst;
  reg [31:0] __synth_literal_61 = $anyconst;
  reg [31:0] __synth_literal_62 = $anyconst;
  reg [31:0] __synth_literal_63 = $anyconst;
  reg __synth_literal_64 = $anyconst;
  reg [31:0] __synth_literal_65 = $anyconst;
  reg [31:0] __synth_literal_66 = $anyconst;
  reg [31:0] __synth_literal_67 = $anyconst;
  reg [31:0] __synth_literal_68 = $anyconst;
  reg __synth_literal_69 = $anyconst;
  reg [31:0] __synth_literal_70 = $anyconst;
  reg [2:0] __synth_literal_71 = $anyconst;
  reg [2:0] __synth_literal_72 = $anyconst;
  reg [2:0] __synth_literal_73 = $anyconst;
  reg [2:0] __synth_literal_74 = $anyconst;
  reg [7:0] __synth_literal_75 = $anyconst;
  reg [7:0] __synth_literal_76 = $anyconst;
  reg [7:0] __synth_literal_77 = $anyconst;
  reg [7:0] __synth_literal_78 = $anyconst;
  reg [7:0] __synth_literal_79 = $anyconst;
  reg [7:0] __synth_literal_80 = $anyconst;
  reg [7:0] __synth_literal_81 = $anyconst;
  reg [7:0] __synth_literal_82 = $anyconst;
  reg [7:0] __synth_literal_83 = $anyconst;
  reg [7:0] __synth_literal_84 = $anyconst;
  reg [7:0] __synth_literal_85 = $anyconst;
  reg [7:0] __synth_literal_86 = $anyconst;
  reg [7:0] __synth_literal_87 = $anyconst;
  reg [7:0] __synth_literal_88 = $anyconst;
  reg [7:0] __synth_literal_89 = $anyconst;
  reg [7:0] __synth_literal_90 = $anyconst;
  reg [7:0] __synth_literal_91 = $anyconst;
  reg [7:0] __synth_literal_92 = $anyconst;
  reg [7:0] __synth_literal_93 = $anyconst;
  reg [7:0] __synth_literal_94 = $anyconst;
  reg [7:0] __synth_literal_95 = $anyconst;
  reg [7:0] __synth_literal_96 = $anyconst;
  localparam INPUT_DATA_WORD_WIDTH = INPUT_DATA_WIDTH / INPUT_KEEP_WIDTH;
  localparam OUTPUT_DATA_WORD_WIDTH = OUTPUT_DATA_WIDTH / OUTPUT_KEEP_WIDTH;
  localparam EXPAND_BUS = OUTPUT_KEEP_WIDTH > INPUT_KEEP_WIDTH;
  localparam DATA_WIDTH = (EXPAND_BUS)? OUTPUT_DATA_WIDTH : INPUT_DATA_WIDTH;
  localparam KEEP_WIDTH = (EXPAND_BUS)? OUTPUT_KEEP_WIDTH : INPUT_KEEP_WIDTH;
  localparam CYCLE_COUNT = (EXPAND_BUS)? OUTPUT_KEEP_WIDTH / INPUT_KEEP_WIDTH : INPUT_KEEP_WIDTH / OUTPUT_KEEP_WIDTH;
  localparam CYCLE_DATA_WIDTH = DATA_WIDTH / CYCLE_COUNT;
  localparam CYCLE_KEEP_WIDTH = KEEP_WIDTH / CYCLE_COUNT;
  localparam [2:0] STATE_IDLE = 3'd0;
  localparam [2:0] STATE_TRANSFER_IN = 3'd1;
  localparam [2:0] STATE_TRANSFER_OUT = 3'd2;
  reg [2:0] state_reg = STATE_IDLE;
  reg [2:0] state_next;
  reg [7:0] cycle_count_reg = 0;
  reg [7:0] cycle_count_next;
  reg [DATA_WIDTH-1:0] temp_tdata_reg = 0;
  reg [DATA_WIDTH-1:0] temp_tdata_next;
  reg [KEEP_WIDTH-1:0] temp_tkeep_reg = 0;
  reg [KEEP_WIDTH-1:0] temp_tkeep_next;
  reg temp_tlast_reg = 0;
  reg temp_tlast_next;
  reg temp_tuser_reg = 0;
  reg temp_tuser_next;
  reg [OUTPUT_DATA_WIDTH-1:0] output_axis_tdata_int;
  reg [OUTPUT_KEEP_WIDTH-1:0] output_axis_tkeep_int;
  reg output_axis_tvalid_int;
  reg output_axis_tready_int = 0;
  reg output_axis_tlast_int;
  reg output_axis_tuser_int;
  wire output_axis_tready_int_early;
  reg input_axis_tready_reg = 0;
  reg input_axis_tready_next;
  assign input_axis_tready = input_axis_tready_reg;

  always @(*) begin
    state_next = (__synth_change_literal_0)? __synth_literal_0 : STATE_IDLE;
    cycle_count_next = cycle_count_reg;
    temp_tdata_next = temp_tdata_reg;
    temp_tkeep_next = temp_tkeep_reg;
    temp_tlast_next = temp_tlast_reg;
    temp_tuser_next = temp_tuser_reg;
    output_axis_tdata_int = (__synth_change_literal_1)? __synth_literal_1 : 0;
    output_axis_tkeep_int = (__synth_change_literal_2)? __synth_literal_2 : 0;
    output_axis_tvalid_int = (__synth_change_literal_3)? __synth_literal_3 : 0;
    output_axis_tlast_int = (__synth_change_literal_4)? __synth_literal_4 : 0;
    output_axis_tuser_int = (__synth_change_literal_5)? __synth_literal_5 : 0;
    input_axis_tready_next = (__synth_change_literal_6)? __synth_literal_6 : 0;
    case(state_reg)
      (__synth_change_literal_7)? __synth_literal_7 : STATE_IDLE: begin
        if(((__synth_change_literal_8)? __synth_literal_8 : CYCLE_COUNT) == ((__synth_change_literal_9)? __synth_literal_9 : 1)) begin
          input_axis_tready_next = output_axis_tready_int_early;
          output_axis_tdata_int = input_axis_tdata;
          output_axis_tkeep_int = input_axis_tkeep;
          output_axis_tvalid_int = input_axis_tvalid;
          output_axis_tlast_int = input_axis_tlast;
          output_axis_tuser_int = input_axis_tuser;
          state_next = (__synth_change_literal_10)? __synth_literal_10 : STATE_IDLE;
        end else if((__synth_change_literal_11)? __synth_literal_11 : EXPAND_BUS) begin
          input_axis_tready_next = (__synth_change_literal_12)? __synth_literal_12 : 1;
          if(input_axis_tvalid) begin
            temp_tdata_next = input_axis_tdata;
            temp_tkeep_next = input_axis_tkeep;
            temp_tlast_next = input_axis_tlast;
            temp_tuser_next = input_axis_tuser;
            cycle_count_next = (__synth_change_literal_13)? __synth_literal_13 : 1;
            if(input_axis_tlast) begin
              input_axis_tready_next = (__synth_change_literal_14)? __synth_literal_14 : 0;
              state_next = (__synth_change_literal_15)? __synth_literal_15 : STATE_TRANSFER_OUT;
            end else begin
              input_axis_tready_next = (__synth_change_literal_16)? __synth_literal_16 : 1;
              state_next = (__synth_change_literal_17)? __synth_literal_17 : STATE_TRANSFER_IN;
            end
          end else begin
            state_next = (__synth_change_literal_18)? __synth_literal_18 : STATE_IDLE;
          end
        end else begin
          input_axis_tready_next = (__synth_change_literal_19)? __synth_literal_19 : 1;
          if(input_axis_tvalid) begin
            cycle_count_next = (__synth_change_literal_20)? __synth_literal_20 : 0;
            temp_tdata_next = input_axis_tdata;
            temp_tkeep_next = input_axis_tkeep;
            temp_tlast_next = input_axis_tlast;
            temp_tuser_next = input_axis_tuser;
            output_axis_tdata_int = input_axis_tdata;
            output_axis_tkeep_int = input_axis_tkeep;
            output_axis_tvalid_int = (__synth_change_literal_21)? __synth_literal_21 : 1;
            output_axis_tlast_int = input_axis_tlast & ((((__synth_change_literal_22)? __synth_literal_22 : CYCLE_COUNT) == ((__synth_change_literal_23)? __synth_literal_23 : 1)) | (input_axis_tkeep[CYCLE_KEEP_WIDTH-1:0] != { CYCLE_KEEP_WIDTH{ (__synth_change_literal_24)? __synth_literal_24 : 1'b1 } }));
            output_axis_tuser_int = input_axis_tuser & ((((__synth_change_literal_25)? __synth_literal_25 : CYCLE_COUNT) == ((__synth_change_literal_26)? __synth_literal_26 : 1)) | (input_axis_tkeep[CYCLE_KEEP_WIDTH-1:0] != { CYCLE_KEEP_WIDTH{ (__synth_change_literal_27)? __synth_literal_27 : 1'b1 } }));
            if(output_axis_tready_int) begin
              cycle_count_next = (__synth_change_literal_28)? __synth_literal_28 : 1;
            end 
            input_axis_tready_next = (__synth_change_literal_29)? __synth_literal_29 : 0;
            state_next = (__synth_change_literal_30)? __synth_literal_30 : STATE_TRANSFER_OUT;
          end else begin
            state_next = (__synth_change_literal_31)? __synth_literal_31 : STATE_IDLE;
          end
        end
      end
      (__synth_change_literal_32)? __synth_literal_32 : STATE_TRANSFER_IN: begin
        input_axis_tready_next = (__synth_change_literal_33)? __synth_literal_33 : 1;
        if(input_axis_tvalid) begin
          temp_tdata_next[cycle_count_reg*CYCLE_DATA_WIDTH +: CYCLE_DATA_WIDTH] = input_axis_tdata;
          temp_tkeep_next[cycle_count_reg*CYCLE_KEEP_WIDTH +: CYCLE_KEEP_WIDTH] = input_axis_tkeep;
          temp_tlast_next = input_axis_tlast;
          temp_tuser_next = input_axis_tuser;
          cycle_count_next = cycle_count_reg + ((__synth_change_literal_34)? __synth_literal_34 : 1);
          if((cycle_count_reg == ((__synth_change_literal_35)? __synth_literal_35 : CYCLE_COUNT) - ((__synth_change_literal_36)? __synth_literal_36 : 1)) | input_axis_tlast) begin
            input_axis_tready_next = output_axis_tready_int_early;
            state_next = (__synth_change_literal_37)? __synth_literal_37 : STATE_TRANSFER_OUT;
          end else begin
            input_axis_tready_next = (__synth_change_literal_38)? __synth_literal_38 : 1;
            state_next = (__synth_change_literal_39)? __synth_literal_39 : STATE_TRANSFER_IN;
          end
        end else begin
          state_next = (__synth_change_literal_40)? __synth_literal_40 : STATE_TRANSFER_IN;
        end
      end
      (__synth_change_literal_41)? __synth_literal_41 : STATE_TRANSFER_OUT: begin
        if((__synth_change_literal_42)? __synth_literal_42 : EXPAND_BUS) begin
          input_axis_tready_next = (__synth_change_literal_43)? __synth_literal_43 : 0;
          output_axis_tdata_int = temp_tdata_reg;
          output_axis_tkeep_int = temp_tkeep_reg;
          output_axis_tvalid_int = (__synth_change_literal_44)? __synth_literal_44 : 1;
          output_axis_tlast_int = temp_tlast_reg;
          output_axis_tuser_int = temp_tuser_reg;
          if(output_axis_tready_int) begin
            if(input_axis_tready & input_axis_tvalid) begin
              temp_tdata_next = input_axis_tdata;
              temp_tkeep_next = input_axis_tkeep;
              temp_tlast_next = input_axis_tlast;
              temp_tuser_next = input_axis_tuser;
              cycle_count_next = (__synth_change_literal_45)? __synth_literal_45 : 1;
              if(input_axis_tlast) begin
                input_axis_tready_next = (__synth_change_literal_46)? __synth_literal_46 : 0;
                state_next = (__synth_change_literal_47)? __synth_literal_47 : STATE_TRANSFER_OUT;
              end else begin
                input_axis_tready_next = (__synth_change_literal_48)? __synth_literal_48 : 1;
                state_next = (__synth_change_literal_49)? __synth_literal_49 : STATE_TRANSFER_IN;
              end
            end else begin
              input_axis_tready_next = (__synth_change_literal_50)? __synth_literal_50 : 1;
              state_next = (__synth_change_literal_51)? __synth_literal_51 : STATE_IDLE;
            end
          end else begin
            state_next = (__synth_change_literal_52)? __synth_literal_52 : STATE_TRANSFER_OUT;
          end
        end else begin
          input_axis_tready_next = (__synth_change_literal_53)? __synth_literal_53 : 0;
          output_axis_tdata_int = temp_tdata_reg[cycle_count_reg*((__synth_change_literal_54)?__synth_literal_54:CYCLE_DATA_WIDTH) +: CYCLE_DATA_WIDTH];
          output_axis_tkeep_int = temp_tkeep_reg[cycle_count_reg*((__synth_change_literal_55)?__synth_literal_55:CYCLE_KEEP_WIDTH) +: CYCLE_KEEP_WIDTH];
          output_axis_tvalid_int = (__synth_change_literal_56)? __synth_literal_56 : 1;
          output_axis_tlast_int = temp_tlast_reg & ((cycle_count_reg == ((__synth_change_literal_57)? __synth_literal_57 : CYCLE_COUNT) - ((__synth_change_literal_58)? __synth_literal_58 : 1)) | (temp_tkeep_reg[cycle_count_reg*((__synth_change_literal_59)?__synth_literal_59:CYCLE_KEEP_WIDTH) +: CYCLE_KEEP_WIDTH] != { CYCLE_KEEP_WIDTH{ (__synth_change_literal_60)? __synth_literal_60 : 1'b1 } }));
          output_axis_tuser_int = temp_tuser_reg & ((cycle_count_reg == ((__synth_change_literal_61)? __synth_literal_61 : CYCLE_COUNT) - ((__synth_change_literal_62)? __synth_literal_62 : 1)) | (temp_tkeep_reg[cycle_count_reg*((__synth_change_literal_63)?__synth_literal_63:CYCLE_KEEP_WIDTH) +: CYCLE_KEEP_WIDTH] != { CYCLE_KEEP_WIDTH{ (__synth_change_literal_64)? __synth_literal_64 : 1'b1 } }));
          if(output_axis_tready_int) begin
            cycle_count_next = cycle_count_reg + ((__synth_change_literal_65)? __synth_literal_65 : 1);
            if((cycle_count_reg == ((__synth_change_literal_66)? __synth_literal_66 : CYCLE_COUNT) - ((__synth_change_literal_67)? __synth_literal_67 : 1)) | (temp_tkeep_reg[cycle_count_reg*((__synth_change_literal_68)?__synth_literal_68:CYCLE_KEEP_WIDTH) +: CYCLE_KEEP_WIDTH] != { CYCLE_KEEP_WIDTH{ (__synth_change_literal_69)? __synth_literal_69 : 1'b1 } })) begin
              input_axis_tready_next = (__synth_change_literal_70)? __synth_literal_70 : 1;
              state_next = (__synth_change_literal_71)? __synth_literal_71 : STATE_IDLE;
            end else begin
              state_next = (__synth_change_literal_72)? __synth_literal_72 : STATE_TRANSFER_OUT;
            end
          end else begin
            state_next = (__synth_change_literal_73)? __synth_literal_73 : STATE_TRANSFER_OUT;
          end
        end
      end
      default: begin
      end
    endcase
  end


  always @(posedge clk) begin
    if(rst) begin
      state_reg <= (__synth_change_literal_74)? __synth_literal_74 : STATE_IDLE;
      cycle_count_reg <= (__synth_change_literal_75)? __synth_literal_75 : 0;
      temp_tdata_reg <= (__synth_change_literal_76)? __synth_literal_76 : 0;
      temp_tkeep_reg <= (__synth_change_literal_77)? __synth_literal_77 : 0;
      temp_tlast_reg <= (__synth_change_literal_78)? __synth_literal_78 : 0;
      temp_tuser_reg <= (__synth_change_literal_79)? __synth_literal_79 : 0;
      input_axis_tready_reg <= (__synth_change_literal_80)? __synth_literal_80 : 0;
    end else begin
      state_reg <= state_next;
      input_axis_tready_reg <= input_axis_tready_next;
      temp_tdata_reg <= temp_tdata_next;
      temp_tkeep_reg <= temp_tkeep_next;
      temp_tlast_reg <= temp_tlast_next;
      temp_tuser_reg <= temp_tuser_next;
      cycle_count_reg <= cycle_count_next;
    end
  end

  reg [OUTPUT_DATA_WIDTH-1:0] output_axis_tdata_reg = 0;
  reg [OUTPUT_KEEP_WIDTH-1:0] output_axis_tkeep_reg = 0;
  reg output_axis_tvalid_reg = 0;
  reg output_axis_tlast_reg = 0;
  reg output_axis_tuser_reg = 0;
  reg [OUTPUT_DATA_WIDTH-1:0] temp_axis_tdata_reg = 0;
  reg [OUTPUT_KEEP_WIDTH-1:0] temp_axis_tkeep_reg = 0;
  reg temp_axis_tvalid_reg = 0;
  reg temp_axis_tlast_reg = 0;
  reg temp_axis_tuser_reg = 0;
  assign output_axis_tdata = output_axis_tdata_reg;
  assign output_axis_tkeep = output_axis_tkeep_reg;
  assign output_axis_tvalid = output_axis_tvalid_reg;
  assign output_axis_tlast = output_axis_tlast_reg;
  assign output_axis_tuser = output_axis_tuser_reg;
  assign output_axis_tready_int_early = output_axis_tready | ~temp_axis_tvalid_reg & ~output_axis_tvalid_reg | ~temp_axis_tvalid_reg & ~output_axis_tvalid_int;

  always @(posedge clk) begin
    if(rst) begin
      output_axis_tdata_reg <= (__synth_change_literal_81)? __synth_literal_81 : 0;
      output_axis_tkeep_reg <= (__synth_change_literal_82)? __synth_literal_82 : 0;
      output_axis_tvalid_reg <= (__synth_change_literal_83)? __synth_literal_83 : 0;
      output_axis_tlast_reg <= (__synth_change_literal_84)? __synth_literal_84 : 0;
      output_axis_tuser_reg <= (__synth_change_literal_85)? __synth_literal_85 : 0;
      output_axis_tready_int <= (__synth_change_literal_86)? __synth_literal_86 : 0;
      temp_axis_tdata_reg <= (__synth_change_literal_87)? __synth_literal_87 : 0;
      temp_axis_tkeep_reg <= (__synth_change_literal_88)? __synth_literal_88 : 0;
      temp_axis_tvalid_reg <= (__synth_change_literal_89)? __synth_literal_89 : 0;
      temp_axis_tlast_reg <= (__synth_change_literal_90)? __synth_literal_90 : 0;
      temp_axis_tuser_reg <= (__synth_change_literal_91)? __synth_literal_91 : 0;
    end else begin
      output_axis_tready_int <= output_axis_tready_int_early;
      if(output_axis_tready_int) begin
        if(output_axis_tready | ~output_axis_tvalid_reg) begin
          output_axis_tdata_reg <= output_axis_tdata_int;
          output_axis_tkeep_reg <= output_axis_tkeep_int;
          output_axis_tvalid_reg <= output_axis_tvalid_int;
          output_axis_tlast_reg <= output_axis_tlast_int;
          output_axis_tuser_reg <= output_axis_tuser_int;
        end else begin
          temp_axis_tdata_reg <= output_axis_tdata_int;
          temp_axis_tkeep_reg <= output_axis_tkeep_int;
          temp_axis_tvalid_reg <= output_axis_tvalid_int;
          temp_axis_tlast_reg <= output_axis_tlast_int;
          temp_axis_tuser_reg <= output_axis_tuser_int;
        end
      end else if(output_axis_tready) begin
        output_axis_tdata_reg <= temp_axis_tdata_reg;
        output_axis_tkeep_reg <= temp_axis_tkeep_reg;
        output_axis_tvalid_reg <= temp_axis_tvalid_reg;
        output_axis_tlast_reg <= temp_axis_tlast_reg;
        output_axis_tuser_reg <= temp_axis_tuser_reg;
        temp_axis_tdata_reg <= (__synth_change_literal_92)? __synth_literal_92 : 0;
        temp_axis_tkeep_reg <= (__synth_change_literal_93)? __synth_literal_93 : 0;
        temp_axis_tvalid_reg <= (__synth_change_literal_94)? __synth_literal_94 : 0;
        temp_axis_tlast_reg <= (__synth_change_literal_95)? __synth_literal_95 : 0;
        temp_axis_tuser_reg <= (__synth_change_literal_96)? __synth_literal_96 : 0;
      end 
    end
  end


endmodule

