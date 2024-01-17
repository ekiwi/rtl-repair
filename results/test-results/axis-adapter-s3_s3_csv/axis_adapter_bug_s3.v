

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

  localparam INPUT_DATA_WORD_WIDTH = INPUT_DATA_WIDTH / INPUT_KEEP_WIDTH;
  localparam OUTPUT_DATA_WORD_WIDTH = OUTPUT_DATA_WIDTH / OUTPUT_KEEP_WIDTH;
  localparam EXPAND_BUS = OUTPUT_KEEP_WIDTH > INPUT_KEEP_WIDTH;
  localparam DATA_WIDTH = (EXPAND_BUS)? OUTPUT_DATA_WIDTH : INPUT_DATA_WIDTH;
  localparam KEEP_WIDTH = (EXPAND_BUS)? OUTPUT_KEEP_WIDTH : INPUT_KEEP_WIDTH;
  localparam CYCLE_COUNT = (EXPAND_BUS)? OUTPUT_KEEP_WIDTH / INPUT_KEEP_WIDTH : INPUT_KEEP_WIDTH / OUTPUT_KEEP_WIDTH;
  localparam CYCLE_DATA_WIDTH = DATA_WIDTH / CYCLE_COUNT;
  localparam CYCLE_KEEP_WIDTH = KEEP_WIDTH / CYCLE_COUNT;
  localparam [2:0] STATE_IDLE = 3'd0;localparam [2:0] STATE_TRANSFER_IN = 3'd1;localparam [2:0] STATE_TRANSFER_OUT = 3'd2;
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
    state_next = STATE_IDLE;
    cycle_count_next = cycle_count_reg;
    temp_tdata_next = temp_tdata_reg;
    temp_tkeep_next = temp_tkeep_reg;
    temp_tlast_next = temp_tlast_reg;
    temp_tuser_next = temp_tuser_reg;
    output_axis_tdata_int = 0;
    output_axis_tkeep_int = 0;
    output_axis_tvalid_int = 0;
    output_axis_tlast_int = 0;
    output_axis_tuser_int = 0;
    input_axis_tready_next = 0;
    case(state_reg)
      STATE_IDLE: begin
        if(CYCLE_COUNT == 1) begin
          input_axis_tready_next = output_axis_tready_int_early;
          output_axis_tdata_int = input_axis_tdata;
          output_axis_tkeep_int = input_axis_tkeep;
          output_axis_tvalid_int = input_axis_tvalid;
          output_axis_tlast_int = input_axis_tlast;
          output_axis_tuser_int = input_axis_tuser;
          state_next = STATE_IDLE;
        end else if(EXPAND_BUS) begin
          input_axis_tready_next = 1;
          if(input_axis_tvalid) begin
            temp_tdata_next = input_axis_tdata;
            temp_tkeep_next = input_axis_tkeep;
            temp_tlast_next = input_axis_tlast;
            temp_tuser_next = input_axis_tuser;
            cycle_count_next = 1;
            if(input_axis_tlast) begin
              input_axis_tready_next = 0;
              state_next = STATE_TRANSFER_OUT;
            end else begin
              input_axis_tready_next = 1;
              state_next = STATE_TRANSFER_IN;
            end
          end else begin
            state_next = STATE_IDLE;
          end
        end else begin
          input_axis_tready_next = 1;
          if(input_axis_tvalid) begin
            cycle_count_next = 0;
            temp_tdata_next = input_axis_tdata;
            temp_tkeep_next = input_axis_tkeep;
            temp_tlast_next = input_axis_tlast;
            temp_tuser_next = input_axis_tuser;
            output_axis_tdata_int = input_axis_tdata;
            output_axis_tkeep_int = input_axis_tkeep;
            output_axis_tvalid_int = 1;
            output_axis_tlast_int = input_axis_tlast & ((CYCLE_COUNT == 1) | (input_axis_tkeep[CYCLE_KEEP_WIDTH-1:0] != { CYCLE_KEEP_WIDTH{ 1'b1 } }));
            output_axis_tuser_int = input_axis_tuser & ((CYCLE_COUNT == 1) | (input_axis_tkeep[CYCLE_KEEP_WIDTH-1:0] != { CYCLE_KEEP_WIDTH{ 1'b1 } }));
            if(output_axis_tready_int) begin
              cycle_count_next = 1;
            end 
            input_axis_tready_next = 0;
            state_next = STATE_TRANSFER_OUT;
          end else begin
            state_next = STATE_IDLE;
          end
        end
      end
      STATE_TRANSFER_IN: begin
        input_axis_tready_next = 1;
        if(input_axis_tvalid) begin
          temp_tdata_next[cycle_count_reg*CYCLE_DATA_WIDTH +: CYCLE_DATA_WIDTH] = input_axis_tdata;
          temp_tkeep_next[cycle_count_reg*CYCLE_KEEP_WIDTH +: CYCLE_KEEP_WIDTH] = input_axis_tkeep;
          temp_tlast_next = input_axis_tlast;
          temp_tuser_next = input_axis_tuser;
          cycle_count_next = cycle_count_reg + 1;
          if((cycle_count_reg == CYCLE_COUNT - 1) | input_axis_tlast) begin
            input_axis_tready_next = output_axis_tready_int_early;
            state_next = STATE_TRANSFER_OUT;
          end else begin
            input_axis_tready_next = 1;
            state_next = STATE_TRANSFER_IN;
          end
        end else begin
          state_next = STATE_TRANSFER_IN;
        end
      end
      STATE_TRANSFER_OUT: begin
        if(EXPAND_BUS) begin
          input_axis_tready_next = 0;
          output_axis_tdata_int = temp_tdata_reg;
          output_axis_tkeep_int = temp_tkeep_reg;
          output_axis_tvalid_int = 1;
          output_axis_tlast_int = temp_tlast_reg;
          output_axis_tuser_int = temp_tuser_reg;
          if(output_axis_tready_int) begin
            if(input_axis_tready & input_axis_tvalid) begin
              temp_tdata_next = input_axis_tdata;
              temp_tkeep_next = input_axis_tkeep;
              temp_tlast_next = input_axis_tlast;
              temp_tuser_next = input_axis_tuser;
              cycle_count_next = 1;
              if(input_axis_tlast) begin
                input_axis_tready_next = 0;
                state_next = STATE_TRANSFER_OUT;
              end else begin
                input_axis_tready_next = 1;
                state_next = STATE_TRANSFER_IN;
              end
            end else begin
              input_axis_tready_next = 1;
              state_next = STATE_IDLE;
            end
          end else begin
            state_next = STATE_TRANSFER_OUT;
          end
        end else begin
          input_axis_tready_next = 0;
          output_axis_tdata_int = temp_tdata_reg[cycle_count_reg*CYCLE_DATA_WIDTH +: CYCLE_DATA_WIDTH];
          output_axis_tkeep_int = temp_tkeep_reg[cycle_count_reg*CYCLE_KEEP_WIDTH +: CYCLE_KEEP_WIDTH];
          output_axis_tvalid_int = 1;
          output_axis_tlast_int = temp_tlast_reg & ((cycle_count_reg == CYCLE_COUNT - 1) | (temp_tkeep_reg[cycle_count_reg*CYCLE_KEEP_WIDTH +: CYCLE_KEEP_WIDTH] != { CYCLE_KEEP_WIDTH{ 1'b1 } }));
          output_axis_tuser_int = temp_tuser_reg & ((cycle_count_reg == CYCLE_COUNT - 1) | (temp_tkeep_reg[cycle_count_reg*CYCLE_KEEP_WIDTH +: CYCLE_KEEP_WIDTH] != { CYCLE_KEEP_WIDTH{ 1'b1 } }));
          if(output_axis_tready_int) begin
            cycle_count_next = cycle_count_reg + 1;
            if((cycle_count_reg == CYCLE_COUNT - 1) | (temp_tkeep_reg[cycle_count_reg*CYCLE_KEEP_WIDTH +: CYCLE_KEEP_WIDTH] != { CYCLE_KEEP_WIDTH{ 1'b1 } })) begin
              input_axis_tready_next = 1;
              state_next = STATE_IDLE;
            end else begin
              state_next = STATE_TRANSFER_OUT;
            end
          end else begin
            state_next = STATE_TRANSFER_OUT;
          end
        end
      end
    endcase
  end


  always @(posedge clk) begin
    if(rst) begin
      state_reg <= STATE_IDLE;
      cycle_count_reg <= 0;
      temp_tdata_reg <= 0;
      temp_tkeep_reg <= 0;
      temp_tlast_reg <= 0;
      temp_tuser_reg <= 0;
      input_axis_tready_reg <= 0;
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
      output_axis_tdata_reg <= 0;
      output_axis_tkeep_reg <= 0;
      output_axis_tvalid_reg <= 0;
      output_axis_tlast_reg <= 0;
      output_axis_tuser_reg <= 0;
      output_axis_tready_int <= 0;
      temp_axis_tdata_reg <= 0;
      temp_axis_tkeep_reg <= 0;
      temp_axis_tvalid_reg <= 0;
      temp_axis_tlast_reg <= 0;
      temp_axis_tuser_reg <= 0;
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
        temp_axis_tdata_reg <= 0;
        temp_axis_tkeep_reg <= 0;
        temp_axis_tvalid_reg <= 0;
        temp_axis_tlast_reg <= 0;
        temp_axis_tuser_reg <= 0;
      end 
    end
  end


endmodule

